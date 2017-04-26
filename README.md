<p align="center">
	<img src="https://raw.githubusercontent.com/hayorov/apsconnect-cli/master/assets/logo.png" alt="logo"/>
</p>

# apsconnect-cli
_A command line tool for APS Connector management on Odin Automation._

[![Build Status](https://travis-ci.org/hayorov/apsconnect-cli.svg?branch=master)](https://travis-ci.org/hayorov/apsconnect-cli)

## How to install
from Pypi repository (recommended)
```
pip install apsconnectcli
```

or last development version (early adopter)
```

pip install https://github.com/hayorov/apsconnect-cli/archive/master.zip
```
_Package supports python2.7 and python3 versions._

## Usage
### Setup communication with OA Hub

```
apsconnect init-hub --hub-host HUB_HOST [--user USER] [--pwd PWD] \
                    [--use-tls USE_TLS] [--port PORT] [--aps-host APS_HOST] \
                    [--aps-port APS_PORT] [--use-tls-aps USE_TLS_APS]
```
```
⇒  apsconnect init-hub oa-hub-hostname
Connectivity with Hub RPC API [ok]
Hub version oa-7.1-2188
Connectivity with Hub APS API [ok]
Config saved [/Users/allexx/.aps_config]
```
### Setup communication with k8s cluster

```
apsconnect init-cluster --cluster-endpoint CLUSTER_ENDPOINT \
                        --user USER --pwd PWD --ca-cert CA_CERT_FILE
```
```
⇒  apsconnect init-cluster cluster_endpoint user password ca_cert
Connectivity with k8s cluster api [ok]
k8s cluster version - v1.5.6
Config saved [/Users/allexx/.kube/config]
```
### Install connector-backend in k8s cluster

```
apsconnect install-backend --name NAME --image IMAGE --config-file CONFIG_FILE \
                          [--healthcheck-path HEALTHCHECK_PATH] [--root-path ROOT_PATH] \
                          [--namespace NAMESPACE] [--replicas REPLICAS] [--force FORCE]
```
```
⇒  apsconnect install-backend connector_name image config_file
Loading config file: /Users/allexx/config
Connected to cluster - https://127.222.183.40
Create config [ok]
Create deployment [ok]
Create service [ok]
Checking service availability
.........
Expose service [ok]
Connector backend - http://127.197.49.26/
```
### Import and install aps-frontend instance

```
apsconnect install-frontend --source SOURCE --oauth-key OAUTH_KEY --oauth-secret OAUTH_SECRET \
				            --backend-url BACKEND_URL [--settings-file SETTINGS_FILE] \
				            [--network NETWORK]
```

### Generate Oauth credentials with helper command
```
apsconnect generate-oauth [--namespace]
```
```
⇒  apsconnect generate-oauth test
OAuh key: test-c77e25b1d6974a87b2ff7f58092d6007
Secret:   14089074ca9a4abd80ba45a19baae693
```

_Note that --source gets http(s):// or filepath argument._


### APS Development mode
Allows to use non-TLS connector-backend URL and [other features for debug](http://doc.apsstandard.org/2.2/process/test/tools/mn/#development-mode).
```
⇒ apsconnect aps-devel-mode
APS Development mode ENABLED
```
Disable mode with `--disable`.
```
⇒ apsconnect aps-devel-mode --disable
APS Development mode DISABLED.
```