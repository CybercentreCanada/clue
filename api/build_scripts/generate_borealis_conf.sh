#!/bin/bash

mkdir -p /etc/clue/conf

CLUE_CONF_PATH="/etc/clue/conf/config.yml"



function create_config() {
  CLUE_CONF_DATA="auth:
  service_account:
    enabled: true
    accounts:
      - username: goose
        password: goose
        provider: keycloak


  oauth:
    enabled: true
    providers:
      keycloak:
        audience: clue
        auto_sync: true
        access_token_url: http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/token
        api_base_url: http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/
        authorize_url: http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/auth
        client_id: clue
        client_secret: 09RhSF7tp0ShDdDMCszqI4zk8HMroTTZ
        # May need quotes
        scope: openid offline_access
        jwks_uri: http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/certs
        required_groups:
          - clue_user
        role_map:
          user: clue_user
          admin: clue_admin
        classification_map:
          users-sg: TLP:AMBER+STRICT

logging:
  log_level: INFO
  log_as_json: false

api:
  audit: true
  debug: true
  validate_session_useragent: false
  external_sources:
    - name: test
      classification: TLP:CLEAR
      max_classification: TLP:CLEAR
      url: "http://localhost:5008"
      maintainer: Example <example@example.com>
      documentation_link: http://example.com/
      datahub_link: http://example.com/
"

  echo "Creating $CLUE_CONF_PATH"
  cat <<<$CLUE_CONF_DATA > $CLUE_CONF_PATH
}


write=true
if [[ -f "$CLUE_CONF_PATH" ]]; then
  while [ true ]; do
    read -n 1 -p "$CLUE_CONF_PATH already exists. Overwrite? (y/N) " res
    if [ -z "$res" ]; then
      res="n"
    fi

    case "$res" in
    [yY])
      break
      ;;
    [nN])
      write=false
      break
      ;;
    *)
      echo "Enter a valid response.\n"
      ;;
    esac
  done
fi

if [ "$write" = true ]; then
  create_config
fi

echo "Completed configuration!"
