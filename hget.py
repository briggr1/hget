"""
    Author: Russell Briggs
    github: briggr1
    Last updated: 9/28/2016
"""
from clint.textui import progress, colored, puts
import cmd
import hashlib
from multiprocessing import Process
import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages import urllib3
from shutil import copyfileobj
from time import sleep
from urllib.parse import urlparse


def _create_session():
    urllib3.disable_warnings()
    http = requests.Session()
    http.mount('http://', HTTPAdapter(max_retries=3))
    http.mount('https://', HTTPAdapter(max_retries=3))
    http.headers = {'Accept': 'application/json, */*',
                    'Accept-language': 'en_US',
                    'Content-Type': 'application/octet-stream'}
    return http


def _get_file_size(session, uri):
    try:
        resp = session.get(uri, headers=None, stream=True, verify=False)
        if resp.status_code not in [200, 202, 206]:
            raise Exception(resp.status_code)
        size = resp.headers['Content-length']
        return size
    except Exception as e:
        msg = "Exception occurred while attempting to GET %s" % uri
    raise Exception(msg, e)


def _get_file_chunk(session, uri, localfile, byterange, x):
    try:
        # TODO: depending on the size of the file, determine optimal chunk size
        cs = 8192

        localfile += str(x)
        headers = {'Range': byterange}

        resp = session.get(uri, headers=headers, stream=True, verify=False)

        if resp.status_code not in [200, 202, 206]:
            raise Exception(resp.status_code)

        with open(localfile, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=cs):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
        return resp

    except Exception as e:
        msg = "Exception occurred while attempting to GET %s" % uri
        raise Exception(msg, e)


def _get_file(session, uri, localfile):
    u = urlparse(uri)
    if str(u.scheme).lower() not in ['http', 'https']:
        puts(colored.yellow('%s not supported. Only HTTP\HTTPS sources are currently supported.' % str(u.scheme).upper()))
        return False

    size = int(_get_file_size(session, uri))

    block = size // 10
    chunks = list()
    chunks.append('bytes=0-%i' % block)
    chunks.append('bytes=%i-%i' % ((block+1), (block * 2)))
    chunks.append('bytes=%i-%i' % (((block * 2) + 1), (block * 3)))
    chunks.append('bytes=%i-%i' % (((block * 3) + 1), (block * 4)))
    chunks.append('bytes=%i-%i' % (((block * 4) + 1), (block * 5)))
    chunks.append('bytes=%i-%i' % (((block * 5) + 1), (block * 6)))
    chunks.append('bytes=%i-%i' % (((block * 6) + 1), (block * 7)))
    chunks.append('bytes=%i-%i' % (((block * 7) + 1), (block * 8)))
    chunks.append('bytes=%i-%i' % (((block * 8) + 1), (block * 9)))
    chunks.append('bytes=%i-' % ((block * 9) + 1))

    procs = list()
    for x in range(len(chunks)):
        p = Process(target=_get_file_chunk, args=(session, uri, localfile, chunks[x], x))
        p.start()
        pp = {'proc': p, 'file': localfile + str(x), 'size': block}
        if x == 9:
            pp['size'] = (size - (block * 9))
        procs.append(pp)

    sleep(1)

    for proc in progress.bar(procs, label="downloading"):
        while proc['proc'].is_alive():
            sleep(1)

    with open(localfile, 'wb') as outfile:
        for proc in procs:
            with open(proc['file'], 'rb') as infile:
                copyfileobj(infile, outfile)

    for proc in procs:
        os.remove(proc['file'])


class CLI(cmd.Cmd):

    prompt = "[cli]# "

    def do_exit(self, line):
        return True

    def do_q(self, line):
        return True

    def do_quit(self, line):
        return True

    def do_get(self, line):
        """Quickly downloads large files
        usage:  get <http source file> <local target file>
        ex:     get https://x.com/file.iso /files/file.iso
        """
        words = line.split()
        if len(words) != 2:
            print("Invalid parameters")
            print("Usage: get <http source file> <local target file>")
            print("ex:    get https://x.com/file.iso /files/file.iso")
            return

        uri = words[0]
        localfile = words[1]
        session = _create_session()
        _get_file(session, uri, localfile)

    def do_md5(self, line):
        """ Get the MD5 sum for a file
        usage: md5 <local file>
        """
        words = line.split()
        if len(words) != 1:
            print("Invalid parameters")
            print("Usage: md5 <local file>")
            print("ex:    md5 /files/file.iso")
            return

        fname = words[0]

        if not os.path.exists(fname):
            puts(colored.yellow('%s does not exist.' % fname))
            return False

        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        puts(colored.green(hash_md5.hexdigest()))

    def do_proxy(self, line):
        """Set an http+https proxy for the request(s).
        usage: proxy <proxy and port> OR proxy default
        ex:    proxy my-proxy.my-domain.com:8088
        """
        words = line.split()
        if len(words) != 1:
            print("Invalid parameters")
            print("Usage: proxy <proxy and port>")
            print("ex:    proxy proxy.x.com:8088")
            return

        proxy = words[0]

        os.environ['HTTP_PROXY'] = 'http://' + proxy
        os.environ['HTTPS_PROXY'] = 'https://' + proxy

        puts(colored.green('proxy set to: %s' % proxy))

    def emptyline(self):
        pass

if __name__ == '__main__':
    print("faster big file downloader")

    try:
        CLI().cmdloop()
    finally:
        print("goodbye")
