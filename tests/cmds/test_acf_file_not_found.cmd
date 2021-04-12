require auth

## Access security environment variables
epicsEnvSet("PATH_TO_ASG_FILES", "$(auth_DIR)")
# Use non existing file
epicsEnvSet("ASG_FILENAME", "$(ASG_FILENAME=unknown_access.acf)")

# set up access security
# disable for now due to failing test
iocshLoad("$(auth_DIR)/accessSecurityGroup.iocsh", "ASG_PATH=$(PATH_TO_ASG_FILES),ASG_FILE=$(ASG_FILENAME)")
