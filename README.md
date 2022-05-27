# joplin-mail-python
Python script that parses e-mail and attachments from _maildir_ files into markdown and imports them into Joplin using the Web Clipper's REST API. Work-in-Progress.

## Dependencies:
- [`mailbox`](https://docs.python.org/3/library/mailbox.html)
  - Currently used for parsing maildir files obtained through `getmail`. 
- `os`
- `re`
  - Used to search within email subject for symbols, similarly to [Evernote's implementation](https://help.evernote.com/hc/en-us/articles/209005347-Save-emails-into-Evernote).
- [`joppy`](https://github.com/marph91/joppy)
  -  A Pythonic API Client for the [Joplin Web Clipper](https://joplinapp.org/api/references/rest_api/)
- [`markdownify`](https://github.com/matthewwithanm/python-markdownify)
  -  For handling `html` emails with (relative) correctness.

Developed using `python 3.10.4`.

## Current Roadblocks

- [`getmail`](https://pyropus.ca./software/getmail/) is a major portability issue.
  - Requires [Cygwin](https://www.cygwin.com/) to be installed on Windows machines.
  - Depends on Python 2. [`getmail6`](https://github.com/getmail6/getmail6) attempts to port the module to 3.x, but it was buggy in my experience.

- Handling weird HTML from certain e-mail providers (Looking at you, outlook!)
  - [`html-sanitizer`](https://github.com/matthiask/html-sanitizer/) seemed to convert a lot of this oddness, but left random artefacts within my test e-mail.
    - It additionally does not allow text to be both bolded and italicized.

- Handling `inline` images on HTML emails.
  - These can be extracted and saved as attachments, but markdownify will still leave the referal links in.
  - [A cursory glance](https://mailtrap.io/blog/embedding-images-in-html-email-have-the-rules-changed/) shows that there are several methods of doing so.
    - both `cid` and `base64` links can be detected with Regex, and replaced with Joplin's own embed format (`:/c04c9b33c73e47f3911486abf6238c9b`).
    - base64 requires we note the original base64 string of the inline attachment to search with!
