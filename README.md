# immich-image

## Update Python requirements
python3 -m pip install -r requirements.txt

## HA devcontainer setup
"mounts": [
    // Custom configuration directory
    "source=${localEnv:HOME}/projects/immich-image/custom_components,target=${containerWorkspaceFolder}/config/custom_components,type=bind"
]