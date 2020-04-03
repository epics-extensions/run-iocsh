require ess

## Access security environment variables
epicsEnvSet("PATH_TO_ASG_FILES", "$(ess_DIR)")
# Use non existing file
epicsEnvSet("ASG_FILENAME", "$(ASG_FILENAME=unknown_access.acf)")

# set up access security
# disable for now due to failing test
iocshLoad("$(ess_DIR)/accessSecurityGroup.iocsh", "ASG_PATH=$(PATH_TO_ASG_FILES),ASG_FILE=$(ASG_FILENAME)")
