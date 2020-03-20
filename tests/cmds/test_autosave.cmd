require autosave

epicsEnvSet("IOCNAME", "myioc")
epicsEnvSet("AS_TOP", "/tmp")

iocshLoad("$(autosave_DIR)/autosave.iocsh", "AS_TOP=$(AS_TOP), IOCNAME=$(IOCNAME)")

iocInit()
