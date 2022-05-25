import mailbox
import os
import re
import json
from joppy import api, tools
from markdownify import markdownify as md

apiInstance = api.Api(token="4dd0092ea436f608e4281c8c75f7a4840ee78cd499e63ae60aa9fce5ac320b1400d35f6007ef90471c75c25f2228ac4e8dde8dd98650b75cdab260dace996466")
if apiInstance.ping().status_code != 200: #Check if Joplin is running
    raise Exception("Joplin Web Clipper service not running.")
else:
    print("Joplin Web Clipper running!")

    folderList = apiInstance.get_all_folders()
    tagList = apiInstance.get_all_tags()

    tagRegex = '(?<=\s\#)\S.+?(?=\s[\!\#\@]|$)'
    folderRegex = '(?<=\s\@)\S.+?(?=\s[\!\#\@]|$)'
    reminderRegex = '(?<=\s\!)\S.+?(?=\s[\!\#\@]|$)'

    folderID = 'a662e883ace74abd840c31e44f3e8739'
    folderName = ""
    tags = ""

    htmlFound = False
    maildir = mailbox.Maildir('C:\cygwin64\home\Jordan Foster\maildir')
    keyIter = maildir.iterkeys()
    msg = mailbox.MaildirMessage
    while True:
        try:
            key = next(keyIter)
            msg = maildir.get(key)
            msgSubject = msg.__getitem__('Subject')
            tagSet = set(re.findall(tagRegex, msgSubject))
            folderSet = set(re.findall(folderRegex, msgSubject))
            reminderSet = set(re.findall(reminderRegex, msgSubject))
            noteDict = dict({
                'folders':[],
                'tags':[],
                'reminders':[],
            })

            #print(folderSet, tagSet, reminderSet)

            for element in folderSet:
                folderPresent = False
                for dict in folderList:
                    if dict.get('title') == element:
                        folderPresent = True
                        noteDict['folders'].append(dict.get('id'))
                        break

                if folderPresent == False:
                    noteDict['folders'].append(apiInstance.add_folder(title=element))

            for element in tagSet:
                tagPresent = False
                for dict in tagList:
                    if dict.get('title') == element:
                        noteDict['tags'].append(dict.get('id'))

            noteHeader = f"""***
            **To:** {msg.__getitem__('To')}
            **Subject:** {msgSubject}
            **From:** {msg.__getitem__('From')}
            **Date:** {msg.__getitem__('Date')}
            **Message-id:** {msg.__getitem__('Message-id')}

            **Tags: 
            ***\n"""

            for part in msg.walk():
                if part.get_content_type() == 'text/plain' and htmlFound == False:
                    filePath = os.path.join('C:\cygwin64\home\Jordan Foster\\', f'{msg.get_filename()}-{part.get_content_subtype()}.txt')
                    noteContents = part.get_payload()
                    writer = open(filePath, "w")
                    writer.write(noteContents)
                    writer.close()
                elif part.get_content_type() == 'text/html':
                    htmlFound = True
                    filePath = os.path.join('C:\cygwin64\home\Jordan Foster\\', f'{msg.get_filename()}-{part.get_content_subtype()}.md')
                    noteContents = md(part.get_payload(decode=True))
                if part.get_content_disposition() == 'attachment':
                    filePath = os.path.join('C:\cygwin64\home\Jordan Foster\\', part.get_filename())
                    attachmentWriter = open(filePath, 'wb')
                    attachmentWriter.write(part.get_payload(decode=True))
                    attachmentWriter.close()            
            dirStr = os.path.join('C:\cygwin64\home\Jordan Foster', 'output.md')
            writer = open(dirStr, "wb")
            writer.write(noteContents.encode('utf-8'))
            writer.close()
        except KeyError as ke:
            print(ke)
            break

