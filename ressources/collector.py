from datetime import datetime
from datetime import timezone
from paramiko import SSHClient
from scp import SCPClient

import json
import os
import paramiko
import re
import requests
import time
import urllib.request


### Settings
## General Settings
refreshInterval = int(os.environ.get('RefreshInterval'))

## SSH Settings
ssh = SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

## Node Settings
name = os.environ.get('NodeName')
url = os.environ.get('NodeURL')

def writeToDatabase(data):
    print(data)
    requests.post("http://" + os.environ.get('DBServer') + ":" + os.environ.get('DBPort') + "/write?db=" + os.environ.get('DBName'), data=data)


while True:
    startTime = time.time()

    if os.environ.get("Remote").lower() == "true":
        ## Get Logfile
        ssh.connect(os.environ.get('SSHServer'), username=os.environ.get('SSHUsername'), password=os.environ.get('SSHPassword'))
        scp = SCPClient(ssh.get_transport())
        scp.get(os.environ.get('SSHLog'), os.environ.get('NodeName') + ".log")
        scp.close()
        ssh.close()

    logfile = open(os.environ.get('NodeName') + ".log", "r").read()

    ### Collect Informations from logfile
    ## Edit the following line in the config.yaml
    ## log.output: "/app/config/node.log"

    # Audit
    auditSuccess = re.findall(r'\sdownloaded\s.*"GET_AUDIT"', string=logfile)
    auditFailedWarn = re.findall(r'\sfailed\s.*"GET_AUDIT"', string=logfile)
    auditFailedCrit = re.findall(r'\sfailed\s.*"GET_AUDIT"', string=logfile)
    writeToDatabase("audit,node=" + name + " success=" + str(len(auditSuccess)) + ",warn=" + str(len(auditFailedWarn)) + ",crit=" + str(len(auditFailedCrit)))

    # Download
    downloadSuccess = re.findall(r'\sdownloaded\s.*"GET"', string=logfile)
    downloadFailed = re.findall(r'\sdownload failed\s.*"GET"', string=logfile)
    downloadCanceled = re.findall(r'\sdownload canceled\s.*"GET"', string=logfile)
    writeToDatabase("download,node=" + name + " success=" + str(len(downloadSuccess)) + ",canceled=" + str(len(downloadCanceled)) + ",failed=" + str(len(downloadFailed)))

    # Upload
    uploadSuccess = re.findall(r'\suploaded\s.*"PUT"', string=logfile)
    uploadRejected = re.findall(r'\supload rejected\s.*"PUT"', string=logfile)
    uploadCanceled = re.findall(r'\supload canceled\s.*"PUT"', string=logfile)
    uploadFailed = re.findall(r'\supload failed\s.*"PUT"', string=logfile)
    writeToDatabase("upload,node=" + name + " success=" + str(len(uploadSuccess)) + ",canceled=" + str(len(uploadCanceled)) + ",failed=" + str(len(uploadFailed)) + ",rejected=" + str(len(uploadRejected)))

    # Download Repair
    downloadRepairSuccess = re.findall(r'\sdownloaded\s.*"GET_REPAIR"', string=logfile)
    downloadRepairCanceled = re.findall(r'\sdownload canceled\s.*"GET_REPAIR"', string=logfile)
    downloadRepairFailed = re.findall(r'\sdownload failed\s.*"GET_REPAIR"', string=logfile)
    writeToDatabase("downloadRepair,node=" + name + " success=" + str(len(downloadRepairSuccess)) + ",canceled=" + str(len(downloadRepairCanceled)) + ",failed=" + str(len(downloadRepairFailed)))

    # Upload Repair
    uploadRepairSuccess = re.findall(r'\suploaded\s.*"PUT_REPAIR"', string=logfile)
    uploadRepairCanceled = re.findall(r'\suploaded canceled\s.*"PUT_REPAIR"', string=logfile)
    uploadRepairFailed = re.findall(r'\suploaded failed\s.*"PUT_REPAIR"', string=logfile)
    writeToDatabase("uploadRepair,node=" + name + " success=" + str(len(uploadRepairSuccess)) + ",canceled=" + str(len(uploadRepairCanceled)) + ",failed=" + str(len(uploadRepairFailed)))

    # Delete
    deleteSuccess = re.findall(r'\sdelete\s.*"PUT_REPAIR"', string=logfile)
    deleteFailed = re.findall(r'\sdelete failed\s.*"PUT_REPAIR"', string=logfile)
    writeToDatabase("delete,node=" + name + " success=" + str(len(deleteSuccess)) + ",failed=" + str(len(deleteFailed)))



    ### Collect Informations from Web-API
    ## Can be activated by exposing the API Port
    ## Add the following line to your docker start command
    ## -p 14002:14002

    # Get General API
    response = urllib.request.urlopen(url + "/api/sno")
    html = response.read()
    output_json = json.loads(html)

    # Uptime
    startedAt = output_json["startedAt"][:19]
    startedAtFormated = datetime.strptime(startedAt, "%Y-%m-%dT%H:%M:%S")
    uptime = datetime.now().replace(tzinfo=timezone.utc).timestamp() - startedAtFormated.replace(tzinfo=timezone.utc).timestamp()
    writeToDatabase("uptime,node=" + name + " uptime=" + str(uptime))
            
    # Disk Space
    diskSpaceUsed = output_json["diskSpace"]["used"]
    diskSpaceTrash = output_json["diskSpace"]["trash"]
    diskSpaceAvailable = output_json["diskSpace"]["available"]
    writeToDatabase("space,node=" + name + " used=" + str(diskSpaceUsed) + ",trash=" + str(diskSpaceTrash) + ",available=" + str(diskSpaceAvailable))

    time.sleep(refreshInterval - (time.time() - startTime))