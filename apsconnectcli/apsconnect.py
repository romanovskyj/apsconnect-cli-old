from __future__ import print_function

import json
import os
import sys
import time
import copy
import uuid
import base64
import warnings
import zipfile
from shutil import copyfile
from xml.etree import ElementTree as xml_et
from datetime import datetime, timedelta

import fire
import yaml
import osaapi
from requests import request, get

from kubernetes import client, config
from kubernetes.client.rest import ApiException

if sys.version_info >= (3,):
    import tempfile
    import xmlrpc.client as xmlrpclib
    from tempfile import TemporaryDirectory
else:
    import xmlrpclib
    import tempfile
    from backports.tempfile import TemporaryDirectory

warnings.filterwarnings('ignore')

CFG_FILE_PATH = os.path.expanduser('~/.aps_config')
KUBE_DIR_PATH = os.path.expanduser('~/.kube')
KUBE_FILE_PATH = '{}/config'.format(KUBE_DIR_PATH)
RPC_CONNECT_PARAMS = ('host', 'user', 'password', 'ssl', 'port')
APS_CONNECT_PARAMS = ('aps_host', 'aps_port', 'use_tls_aps')
AUTH_TEMPLATE = {
    'apiVersion': 'v1',
    'clusters': [
        {
            'cluster': {
                'api-version': 'v1',
                'certificate-authority-data': '{BASE64CERT}',
                'server': '{ENDPOINT}',
            },
            'name': 'cluster',
        },
    ],
    'contexts': [
        {
            'context': {
                'cluster': 'cluster',
                'user': 'cluster-admin',
            },
            'name': 'cluster-context',
        },
    ],
    'current-context': 'cluster-context',
    'kind': 'Config',
    'preferences': {},
    'users': [
        {
            'name': 'cluster-admin',
            'user': {
                'username': '{USERNAME}',
                'password': '{PASSWORD}',
            },
        },
    ],
}


class APSConnectUtil:
    """ A command line tool for APS connector installation on Odin Automation in the relaxed way"""

    def init_cluster(self, cluster_endpoint, user, pwd, ca_cert):
        """ Connect your kubernetes (k8s) cluster"""
        try:
            with open(ca_cert) as _file:
                ca_cert_data = base64.b64encode(_file.read().encode())
        except Exception as e:
            print("Unable to read ca_cert file, error: {}".format(e))
            sys.exit(1)

        auth_template = copy.deepcopy(AUTH_TEMPLATE)
        cluster = auth_template['clusters'][0]['cluster']
        user_data = auth_template['users'][0]['user']

        cluster['certificate-authority-data'] = ca_cert_data.decode()
        cluster['server'] = 'https://{}'.format(cluster_endpoint)
        user_data['username'] = user
        user_data['password'] = pwd

        _, temp_config = tempfile.mkstemp()
        with open(temp_config, 'w') as fd:
            yaml.safe_dump(auth_template, fd)

        try:
            api_client = _get_k8s_api_client(temp_config)
            api = client.VersionApi(api_client)
            code = api.get_code()
            print("Connectivity with k8s cluster api [ok]")
            print("k8s cluster version - {}".format(code.git_version))
        except Exception as e:
            print("Unable to communicate with k8s cluster {}, error: {}".format(
                cluster_endpoint, e))
            sys.exit(1)

        os.remove(temp_config)

        if not os.path.exists(KUBE_DIR_PATH):
            os.mkdir(KUBE_DIR_PATH)
            print("Created directory [{}]".format(KUBE_DIR_PATH))

        with open(KUBE_FILE_PATH, 'w+') as fd:
            yaml.safe_dump(auth_template, fd)
            print("Config saved [{}]".format(KUBE_FILE_PATH))

    def init_hub(self, hub_host, user='admin', pwd='1q2w3e', use_tls=False, port=8440,
                 aps_host=None, aps_port=6308, use_tls_aps=True):
        """ Connect your Odin Automation Hub"""
        if not aps_host:
            aps_host = hub_host
        use_tls = use_tls in ('Yes', 'True', '1')
        hub = osaapi.OSA(host=hub_host, user=user, password=pwd, ssl=use_tls, port=port)
        try:
            hub_version = _get_hub_version(hub)
            print("Connectivity with Hub RPC API [ok]")
            _assert_hub_version(hub_version)
            print("Hub version {}".format(hub_version))
            r = request('GET', '{}/{}'.format(_get_aps_url(aps_host, aps_port, use_tls_aps),
                                              'aps/2/applications/'),
                        headers=_get_user_token(hub, user), verify=False)
            r.raise_for_status()
            print("Connectivity with Hub APS API [ok]")

        except Exception as e:
            print("Unable to communicate with hub {}, error: {}".format(hub_host, e))
            sys.exit(1)

        with open(CFG_FILE_PATH, 'w+') as cfg:
            cfg.write(json.dumps({'host': hub_host, 'user': user, 'password': pwd, 'ssl': use_tls,
                                  'port': port, 'aps_port': aps_port, 'aps_host': aps_host,
                                  'use_tls_aps': use_tls_aps},
                                 indent=4))
            print("Config saved [{}]".format(CFG_FILE_PATH))

    def install_backend(self, name, image, config_file, healthcheck_path='/',
                        root_path='/', namespace='default', replicas=2,
                        force=False):
        """ Install connector-backend in the k8s cluster"""

        try:
            config_data = json.load(open(config_file))
            print("Loading config file: {}".format(config_file))
        except Exception as e:
            print("Unable to read config file, error: {}".format(e))
            sys.exit(1)

        api_client = _get_k8s_api_client()
        api = client.VersionApi(api_client)
        core_v1 = client.CoreV1Api(api_client)
        ext_v1 = client.ExtensionsV1beta1Api(api_client)

        try:
            api.get_code()
            print("Connected to cluster - {}".format(api_client.host))
        except Exception as e:
            print("Unable to communicate with k8s cluster, error: {}".format(e))
            sys.exit(1)

        try:
            _create_secret(name, config_data, core_v1, namespace, force)
            print("Create config [ok]")
        except Exception as e:
            print("Can't create config in cluster, error: {}".format(e))
            sys.exit(1)

        try:
            _create_deployment(name, image, ext_v1, healthcheck_path, replicas,
                               namespace, force, core_api=core_v1)
            print("Create deployment [ok]")
        except Exception as e:
            print("Can't create deployment in cluster, error: {}".format(e))
            sys.exit(1)

        try:
            _create_service(name, core_v1, namespace, force)
            print("Create service [ok]")
        except Exception as e:
            print("Can't create deployment in cluster, error: {}".format(e))
            sys.exit(1)

        print("Checking service availability")

        try:
            ip = _polling_service_access(name, core_v1, namespace, timeout=180)
            print("Expose service [ok]")
            print("Connector backend - http://{}/{}".format(ip, root_path.lstrip('/')))
        except Exception as e:
            print("Service expose FAILED, error: {}".format(e))
            sys.exit(1)

        print("[Success]")

    def install_frontend(self, source, oauth_key, oauth_secret, backend_url, settings_file=None,
                         network='public'):
        """ Install connector-frontend in Odin Automation Hub, --source can be http(s):// or
        filepath"""

        with TemporaryDirectory() as tdir:
            is_http_source = True if source.startswith('http://') or source.startswith('https://') \
                else False

            if is_http_source:
                package_name = _download_file(source, target=tdir)
            else:
                package_name = os.path.basename(source)
                copyfile(os.path.expanduser(source), os.path.join(tdir, package_name))

            package_path = os.path.join(tdir, package_name)
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                meta_path = zip_ref.extract('APP-META.xml', path=tdir)

            tree = xml_et.ElementTree(file=meta_path)
            namespace = '{http://aps-standard.org/ns/2}'
            connector_id = tree.find('{}id'.format(namespace)).text
            version = tree.find('{}version'.format(namespace)).text
            release = tree.find('{}release'.format(namespace)).text

            if not settings_file:
                settings_file = {}
            else:
                settings_file = json.load(open(settings_file))

            if backend_url.startswith('http://'):
                print("WARN: Make sure that the APS development mode enabled for http backend. "
                      "Run `apsconnect aps_devel_mode` command.")
            elif backend_url.startswith('https://'):
                pass
            else:
                print("Backend url must be URL http(s)://, got {}".format(backend_url))
                sys.exit(1)

            cfg, hub = _get_cfg(), _get_hub()

            with open(package_path, 'rb') as package_binary:
                print("Importing connector {} {}-{}".format(connector_id, version, release))
                import_kwargs = {'package_url': source} if is_http_source \
                    else {'package_body': xmlrpclib.Binary(package_binary.read())}
                r = hub.APS.importPackage(**import_kwargs)
                _osaapi_raise_for_status(r)

                print("Connector {} imported with id={}"
                      .format(connector_id, r['result']['application_id']))

            payload = {
                "aps": {
                    "package": {
                        "type": connector_id,
                        "version": version,
                        "release": release,
                    },
                    "endpoint": backend_url,
                    "network": network,
                    "auth": {
                        "oauth": {
                            "key": oauth_key,
                            "secret": oauth_secret,
                        }
                    }
                }
            }

            payload.update(settings_file)

            base_aps_url = _get_aps_url(**{k: _get_cfg()[k] for k in APS_CONNECT_PARAMS})

            r = request(method='POST', url='{}/{}'.format(base_aps_url, 'aps/2/applications/'),
                        headers=_get_user_token(hub, cfg['user']), verify=False, json=payload)
            try:
                r.raise_for_status()
                print("[Success]")
            except Exception as e:
                if 'error' in r.json():
                    err = "{} {}".format(r.json()['error'], r.json()['message'])
                else:
                    err = str(e)
                print("Installation of connector {} FAILED.\n"
                      "Hub APS API response {} code.\n"
                      "Error: {}".format(connector_id, r.status_code, err))

    def generate_oauth(self, namespace=''):
        """ Helper for Oauth credentials generation"""
        if namespace:
            namespace += '-'
        print("OAuh key: {}{}\nSecret: {}".format(namespace, uuid.uuid4().hex, uuid.uuid4().hex))

    def aps_devel_mode(self, disable=False):
        """ Enable development mode for OA Hub"""
        hub = _get_hub()
        r = hub.setSystemProperty(account_id=1, name='APS_DEVEL_MODE', bool_value=not bool(disable))
        _osaapi_raise_for_status(r)
        print("APS Development mode {}.".format('DISABLED' if disable else 'ENABLED'))


def _get_aps_url(aps_host, aps_port, use_tls_aps):
    return '{}://{}:{}'.format('https' if use_tls_aps else 'http', aps_host, aps_port)


def _get_hub_version(hub):
    r = hub.statistics.getStatisticsReport(reports=[{'name': 'report-for-cep', 'value': ''}])
    _osaapi_raise_for_status(r)
    tree = xml_et.fromstring(r['result'][0]['value'])
    return tree.find('ClientVersion').text


def _assert_hub_version(hub_version):
    if not hub_version.startswith('oa-7.1-'):
        print("Hub 7.1 version needed, got {}".format(hub_version))
        sys.exit(1)


def _get_user_token(hub, user):
    # TODO user -> user_id
    r = hub.APS.getUserToken(user_id=1)
    _osaapi_raise_for_status(r)
    return {'APS-Token': r['result']['aps_token']}


def _get_hub():
    return osaapi.OSA(**{k: _get_cfg()[k] for k in RPC_CONNECT_PARAMS})


def _get_k8s_api_client(config_file=None):
    if not config_file:
        config_file = KUBE_FILE_PATH

    return config.new_client_from_config(config_file=config_file)


def _osaapi_raise_for_status(r):
    if r['status']:
        if 'error_message' in r:
            raise Exception("Error: {}".format(r['error_message']))
        else:
            raise Exception("Error: Unknown {}".format(r))


def _download_file(url, target=None):
    local_filename = url.split('/')[-1]
    if target:
        local_filename = os.path.join(target, local_filename)
    r = get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    return local_filename


def _get_cfg():
    cfg = json.load(open(CFG_FILE_PATH))
    if not cfg:
        print("Run init command.")
        sys.exit(1)
    return cfg


def _create_secret(name, data, api, namespace='default', force=False):
    secret = {
        'apiVersion': 'v1',
        'data': {
            'config.json': base64.b64encode(json.dumps(data).encode('utf-8')).decode(),
        },
        'kind': 'Secret',
        'metadata': {
            'name': name,
        },
        'type': 'Opaque',
    }

    if force:
        _delete_secret(name, api, namespace)

    api.create_namespaced_secret(
        namespace=namespace,
        body=secret,
    )


def _delete_secret(name, api, namespace):
    try:
        api.delete_namespaced_secret(
            namespace=namespace,
            body=client.V1DeleteOptions(),
            name=name,
        )
    except ApiException as e:
        if e.status != 404:
            raise


def _create_deployment(name, image, api, healthcheck_path='/', replicas=2,
                       namespace='default', force=False, core_api=None):
    template = {
        'apiVersion': 'extensions/v1beta1',
        'kind': 'Deployment',
        'metadata': {
            'name': name,
        },
        'spec': {
            'replicas': replicas,
            'template': {
                'metadata': {
                    'labels': {
                        'name': name,
                    },
                },
                'spec': {
                    'containers': [
                        {
                            'name': name,
                            'image': image,
                            'env': [
                                {
                                    'name': 'CONFIG_FILE',
                                    'value': '/config/config.json',
                                },
                            ],
                            'livenessProbe': {
                                'httpGet': {
                                    'path': healthcheck_path,
                                    'port': 80,
                                },
                            },
                            'readinessProbe': {
                                'httpGet': {
                                    'path': healthcheck_path,
                                    'port': 80,
                                },
                            },
                            'ports': [
                                {
                                    'containerPort': 80,
                                    'name': 'http-server',
                                },
                            ],
                            'resources': {
                                # TODO increase limits by default
                                'limits': {
                                    'cpu': '100m',
                                    'memory': '128Mi',
                                },
                            },
                            'volumeMounts': [
                                {
                                    'mountPath': '/config',
                                    'name': 'config-volume',
                                },
                            ],
                        },
                    ],
                    'volumes': [
                        {
                            'name': 'config-volume',
                            'secret': {
                                'secretName': name,
                            },
                        },
                    ],
                },
            },
        },
    }

    if force:
        _delete_deployment(name, api=api, namespace=namespace, core_api=core_api)

    api.create_namespaced_deployment(namespace=namespace, body=template)


def _delete_deployment(name, api, namespace, core_api=None):
    try:
        api.delete_namespaced_deployment(
            namespace=namespace,
            name=name,
            body=client.V1DeleteOptions(),
            grace_period_seconds=0,
        )
    except ApiException as e:
        if e.status != 404:
            raise

    replica_set = api.list_namespaced_replica_set(
        namespace=namespace,
        label_selector='name={}'.format(name),
    )

    if len(replica_set.items):
        for rs in replica_set.items:
            rs_name = rs.metadata.name
            api.delete_namespaced_replica_set(namespace=namespace, name=rs_name,
                                              body=client.V1DeleteOptions(),
                                              grace_period_seconds=0)

    pods = core_api.list_namespaced_pod(
        namespace=namespace,
        label_selector='name={}'.format(name)
    )
    pod_names = [pod.metadata.name for pod in pods.items]

    for name in pod_names:
        core_api.delete_namespaced_pod(
            namespace=namespace,
            name=name,
            body=client.V1DeleteOptions(),
            grace_period_seconds=0,
        )


def _create_service(name, api, namespace='default', force=False):
    service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'labels': {
                'name': name,
            },
            'name': name,
        },
        'spec': {
            'ports': [
                {
                    'port': 80,
                    'protocol': 'TCP',
                    'targetPort': 80,
                }
            ],
            'selector': {
                'name': name
            },
            'type': 'LoadBalancer'
        }
    }

    if force:
        _delete_service(name, api, namespace)

    api.create_namespaced_service(namespace=namespace, body=service)


def _delete_service(name, api, namespace):
    try:
        api.delete_namespaced_service(namespace=namespace, name=name)
    except ApiException as e:
        if e.status != 404:
            raise


def _polling_service_access(name, api, namespace, timeout=120):
    max_time = datetime.now() + timedelta(seconds=timeout)

    while True:
        try:
            data = api.read_namespaced_service_status(name=name, namespace=namespace)
            ingress = data.status.load_balancer.ingress

            if ingress:
                print()
                return ingress[0].ip

            sys.stdout.write('.')
            sys.stdout.flush()
        except:
            raise

        if datetime.now() > max_time:
            raise Exception("Waiting time exceeded")

        time.sleep(10)


def main():
    try:
        fire.Fire(APSConnectUtil, name='apsconnect')
    except Exception as e:
        print("Error: {}".format(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
