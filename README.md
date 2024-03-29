<p align="center">
	<img src="https://raw.githubusercontent.com/hayorov/apsconnect-cli/master/assets/logo.png" alt="logo"/>
</p>

# apsconnect-cli
_A command line tool for APS connector installation on Odin Automation in the relaxed way._

[![Build Status](https://travis-ci.org/hayorov/apsconnect-cli.svg?branch=master)](https://travis-ci.org/hayorov/apsconnect-cli)

## How to install
```
pip install apsconnectcli
```


## Usage

#### 1 Connect your kubernetes (k8s) cluster

```
apsconnect init-cluster --cluster-endpoint CLUSTER_ENDPOINT \
                        --user USER --pwd PWD --ca-cert CA_CERT_FILE
```

```
⇒  apsconnect init-cluster k8s.cluster.host k8s-admin password ./my-k8s-cert.pem
Connectivity with k8s cluster api [ok]
k8s cluster version - v1.5.6
Config saved [/Users/allexx/.kube/config]
```

#### 2 Connect your Odin Automation Hub

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

#### 3. Install connector-backend in the k8s cluster

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
#### 4. Install connector-frontend in Odin Automation Hub

```
apsconnect install-frontend --source SOURCE --oauth-key OAUTH_KEY --oauth-secret OAUTH_SECRET \
				            --backend-url BACKEND_URL [--settings-file SETTINGS_FILE] \
				            [--network NETWORK]
```

## Misc

#### Generate Oauth credentials with helper command
```
apsconnect generate-oauth [--namespace]
```
```
⇒  apsconnect generate-oauth test
OAuh key: test-c77e25b1d6974a87b2ff7f58092d6007
Secret:   14089074ca9a4abd80ba45a19baae693
```

_Note that --source gets http(s):// or filepath argument._


#### Enable APS Development mode
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