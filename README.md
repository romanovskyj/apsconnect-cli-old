<p align="center">
	<img src="https://raw.githubusercontent.com/hayorov/apsconnect-cli/master/assets/logo.png" alt="logo"/>
</p>

# apsconnect-cli
_A command line tool for creation aps-frontend instance._

[![Build Status](https://travis-ci.org/hayorov/apsconnect-cli.svg?branch=master)](https://travis-ci.org/hayorov/apsconnect-cli)

## How to install
From pypi.python.org
```
pip install apsconnectcli
```

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
Allows to use non-TLS connect-backend URL and [other features for debug](http://doc.apsstandard.org/2.2/process/test/tools/mn/#development-mode).
```
⇒ apsconnect aps-devel-mode
APS Development mode ENABLED
```
Disable mode with agument `--disable`
```
⇒ apsconnect aps-devel-mode --disable
APS Development mode DISABLED.
```