import mailbox
import os
import re
from joppy import api, tools
from markdownify import markdownify as md
from html_sanitizer import Sanitizer
from dotenv import load_dotenv

load_dotenv()
apiInstance = api.Api(token=os.getenv('JOPLIN_TOKEN'))
rootDir = os.getenv('ROOTDIR')

sanitizerInstance = Sanitizer({
    'tags': {
            'a', 'b', 'blockquote', 'br', 'code', 'em', 
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img',
            'li', 'q', 'strong', 'sub', 'sup', 'table',
            'tbody', 'td', 'th', 'thead', 'title', 'tr',
            'u', 'ul', 'mark', 'p'
    },
    'attributes': {
        'a': ('href','name','target','title','id','rel','alt'),
        'img': ('border','width','height','src','alt')
    },
    'empty': {
        'b','blockquote','br','code','em','h1','h2','h3','h4',
        'h5','h6','li','q','strong','sub','sup','u','ul','img'
    },
})

if apiInstance.ping().status_code != 200: #Check if Joplin is running
    raise Exception("Joplin Web Clipper service not running.")
else:
    print("Joplin Web Clipper running!")

    folderList = apiInstance.get_all_notebooks()
    tagList = apiInstance.get_all_tags()

    tagRegex = '(?<=\s\#)\S.+?(?=\s[\!\#\@]|$)'
    folderRegex = '(?<=\s\@)\S.+?(?=\s[\!\#\@]|$)'
    reminderRegex = '(?<=\s\!)\S.+?(?=\s[\!\#\@]|$)'
    bpRegex = '(if !supportLists\d\.)\s*\n(endif)'
    cidRegex = '(?<=src=\")(cid:\w+\.\w+@\w+\.\w+)(?=\")'
    base64Regex = '(?<=src=\")(data:\w+\/[\w\.\-]+;base64,[\w\-\_]+\=*)(?=\")' #Opinionated on RFC 4648 §5 (base64url)
    folderID = 'a662e883ace74abd840c31e44f3e8739'
    folderName = ""
    tags = ""

    htmlFound = False
    maildir = mailbox.Maildir(f'{rootDir}\maildir')
    outputdir = (f'{rootDir}\output')
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
            inlineList = []
            attachmentList = []

            noteDict = dict({
                'folders':[],
                'tags':[],
                'reminders':[],
            })

            msgDict = dict({
                'to':msg.__getitem__('To'),
                'subject':msg.__getitem__('Subject'),
                'from':msg.__getitem__('From'),
                'date':msg.__getitem__('Date'),
                'message-id':msg.__getitem__('Message-id'),
            })

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
                if part.get_content_disposition() != None:
                    if part.get_content_disposition() == 'inline':
                        inlineName = part.get_param('name')
                        inlineDir = os.path.join(outputdir, inlineName)

                        with open(inlineDir, 'wb') as inline:
                            inline.write(part.get_payload(decode=True))

                        inlineList.append((part.get_param('name'), inlineDir))

                    elif part.get_content_disposition() == 'attachment':
                        attachmentName = part.get_param('name')
                        attachmentDir = os.path.join(outputdir, attachmentName)

                        with open(attachmentDir, 'wb') as attachment:
                            attachment.write(part.get_payload(decode=True))

                        attachmentList.append((part.get_param('name'), attachmentDir))
                
                elif part.get_content_type() == 'text/plain':
                    msgDict['plaintext'] = part.get_payload(decode=True)
                    with open(os.path.join(outputdir, 'plaintext.txt'), 'wb') as plaintextWriter:
                        plaintextWriter.write(msgDict.get('plaintext'))
                elif part.get_content_type() == 'text/html':
                    msgDict['html'] = part.get_payload(decode=True)
                else:
                    print(part.get_content_type())
            
            msgDict['inline'] = inlineList
            msgDict['attachments'] = attachmentList

            for cidMatch in set(re.findall(rb'(?<=src=")(cid:\w+\.\w+@\w+\.\w+)(?=")', msgDict.get('html'))):
                for inlineTuple in msgDict.get('inline'):
                    encodedFilename = inlineTuple[0].encode('utf-8')
                    if cidMatch.__contains__ (encodedFilename):
                        updatedHTML = msgDict.get('html').replace(cidMatch, encodedFilename)
                        msgDict['html'] = updatedHTML
            
            for base64Match in set(re.findall(rb'(?<=src=")(data:\w+\/[\w\.\-]+;base64,[\w\-\_]+\=*)(?=")', msgDict.get('html'))):
                for inlineTuple in msgDict.get('inline'):
                    encodedBase64 = tools.encode_base64(inlineTuple[1]).encode('utf-8')
                    if base64Match.__contains__(encodedBase64):
                        updatedHTML = msgDict.get('html').replace(base64Match, encodedBase64)
                        msgDict['html'] = updatedHTML
            
            with open(os.path.join(outputdir, 'HTML.html'), 'wb') as htmlWriter:
                htmlWriter.write(msgDict.get('html'))

            with open(os.path.join(outputdir, 'html_sanitized.html'), 'w') as sanitizedWriter:
                sanitizedHTML = sanitizerInstance.sanitize(msgDict.get('html').decode('utf-8'))
                sanitizedWriter.write(sanitizedHTML)

            with open(os.path.join(outputdir, 'markdown.md'), 'w') as mdWriter:
                baseMD = md(sanitizedHTML)
                mdWriter.write(baseMD)

            sourceStr = ""
            if msgDict.get('html') != None:
                sourceStr += f'[HTML](:/{apiInstance.add_resource(os.path.join(outputdir, "HTML.html"))})\n'
            if msgDict.get('plaintext') != None:
                sourceStr += f'[TXT](:/{apiInstance.add_resource(os.path.join(outputdir, "plaintext.txt"))})\n'

            joplinMD = sourceStr + '\n***\n' +baseMD

            for inlineTuple in msgDict.get('inline'):
                if joplinMD.__contains__(inlineTuple[0]):
                    joplinMD = joplinMD.replace(inlineTuple[0], f":/{apiInstance.add_resource(inlineTuple[1])}")
            
            joplinMD += '\n***\n'
            for attachmentTuple in msgDict.get('attachments'):
                joplinMD += f'[{attachmentTuple[0]}](:/{apiInstance.add_resource(attachmentTuple[1])})\n'


            
            joplinMD += sourceStr
            apiInstance.add_note(title=msgDict.get('subject'), body=joplinMD)

        except KeyError as ke:
            print(ke)
            break

