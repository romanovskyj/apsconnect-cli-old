<p align="center">
	<img src="https://raw.githubusercontent.com/hayorov/apsconnect-cli/master/assets/logo.png" alt="logo"/>
</p>

# apsconnect-cli
_A command line tool for creation aps-frontend instance._

## How to install
```
pip install https://github.com/hayorov/apsconnect-cli/archive/master.zip
```
_Package supports python2.7 and python3 versions._

## Usage
### Setup communication with OA Hub

```
apsconnect init --hub-host HUB_HOST [--user USER] [--pwd PWD] \
                [--use-tls USE_TLS] [--port PORT] [--aps-host APS_HOST] \
                [--aps-port APS_PORT] [--use-tls-aps USE_TLS_APS]
```

### Import and install aps-frontend instance

```
apsconnect install --source SOURCE --oauth-key OAUTH_KEY --oauth-secret OAUTH_SECRET \
				   --backend-url BACKEND_URL [--settings-file SETTINGS_FILE] \
				   [--network NETWORK]
```

_Note that --source gets http(s):// or file:// argument._