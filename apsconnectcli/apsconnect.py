import json
import os
import sys
import uuid
import warnings
import zipfile
from shutil import copyfile
from xml.etree import ElementTree as xml_et

import fire
import osaapi
from requests import request, get

if sys.version_info >= (3,):
    import tempfile
    import xmlrpc.client as xmlrpclib
else:
    import xmlrpclib
    from backports import tempfile

warnings.filterwarnings('ignore')

CFG_FILE_PATH = os.path.expanduser('~/.aps_config')
RPC_CONNECT_PARAMS = ('host', 'user', 'password', 'ssl', 'port')
APS_CONNECT_PARAMS = ('aps_host', 'aps_port', 'use_tls_aps')


class APSConnectUtil:
    """A command line tool for creation aps-frontend instance"""

    def init_hub(self, hub_host, user='admin', pwd='1q2w3e', use_tls=False, port=8440,
                 aps_host=None, aps_port=6308, use_tls_aps=True):
        """ Setup communication with OA Hub"""
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

    def install_frontend(self, source, oauth_key, oauth_secret, backend_url, settings_file=None,
                         network='public'):
        """ Import and install connector-frontend instance, --source can be http(s):// or
        filepath"""

        with tempfile.TemporaryDirectory() as tdir:
            if not (source.startswith('http://') or source.startswith('https://')):
                package_name = os.path.basename(source)
                copyfile(os.path.expanduser(source), os.path.join(tdir, package_name))
            else:
                package_name = _download_file(source, target=tdir)
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
                print("Backend url must be URL https(s)://, got {}".format(backend_url))
                sys.exit(1)

            cfg, hub = _get_cfg(), _get_hub()

            with open(package_path, 'rb') as package_binary:
                print("Importing connector {} {}-{}".format(connector_id, version, release))
                r = hub.APS.importPackage(package_body=xmlrpclib.Binary(package_binary.read()))
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
        r = hub.setSystemProperty(account_id=1, name='APS_DEVEL_MODE', bool_value=False)
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


def main():
    try:
        fire.Fire(APSConnectUtil, name='apsconnect')
    except Exception as e:
        print("Error: {}".format(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
