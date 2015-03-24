# coding: utf-8
from __future__ import with_statement
import codecs
import json
import os
import platform
import subprocess
import sys

from fabric.api import *
from fabric.colors import *
from fabric.utils import abort
from fabric.contrib.console import confirm

# Examples of Usage
# fab --list
# fab localhost bootstrap
# fab prepare
# fab rename:extension=jpg
# fab resize_imgs:folder=output
# fab compress_imgs
# fab logos

# Environments

@task
def localhost():
    common()
    env.run = local
    env.sudo = local
    read_config_file('localhost.json')
    print(blue("Localhost"))

@task
def staging():
    common()
    if current_git_branch() != 'staging':
        if not confirm('Using staging environment without staging branch (%s). Are you sure?' % current_git_branch()):
            abort('cancelled by the user')
    env.venv = 'envstaging'
    env.python = 'python2.7'
    read_config_file('staging.json')
    print(blue("Staging"))

@task
def production():
    common()
    if current_git_branch() != 'master':
        if not confirm('Using production environment without master branch (%s). Are you sure?' % current_git_branch()):
            abort('cancelled by the user')
    read_config_file('production.json')
    print(blue("Production"))

def common():
    env.run = local
    env.sudo = local
    env.git_repository = ''
    env.app_path = '.'
    env.user = 'ubuntu'
    env.venv = 'env'
    env.python = 'pypy'
    env.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', '')
    env.aws_secret_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
    env.aws_region = os.getenv('AWS_REGION', '')
    env.aws_bucket = 'weblibraries'

def read_config_file(filename):
    """
    Example of the file localhost.json:
    {
        "ami": "123",
        "hosts": ["a.com", "b.com"]
    }
    """
    if os.path.exists(filename):
        with codecs.open(filename, 'r', 'utf-8') as f:
           data = json.loads(f.read())
           print(data)
           env.update(data)


# Utilities

def current_git_branch():
    label = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
    return label.strip()

def isMac():
    return platform.system().lower() == 'darwin'

def isLinux():
    return platform.system().lower() == 'linux'

def venv():
    return 'source %(env)s/bin/activate' % dict(env=env.venv)

def python(command):
  return 'python %(command)s' % dict(command=command)

def manage(command):
  return 'python manage.py %(command)s' % dict(command=command)

def install(packages):
    packages = ' '.join(packages)
    if isMac():
        env.run('brew install %(packages)s' % dict(packages=packages))
    elif isLinux():
        env.sudo('apt-get install -y %(package)s' % dict(package=packages))

def get_or_create_bucket(name, public=True, cors=None):
    with cd(env.app_path), prefix(venv()):
        import boto
        from boto.s3.cors import CORSConfiguration
        conn = boto.connect_s3() # read AWS env vars
        bucket = conn.lookup(name)
        if bucket is None:
            print('Creating bucket %s' % name)
            bucket = conn.create_bucket(name)
            if public:
                bucket.set_acl('public-read')
            if cors:
                cors_cfg = CORSConfiguration()
                cors_cfg.add_rule(['PUT', 'POST', 'DELETE'], cors, allowed_header='*', max_age_seconds=3000, expose_header='x-amz-server-side-encryption')
                cors_cfg.add_rule('GET', '*')
                bucket.set_cors(cors_cfg)
        return bucket

def upload_file_to_s3(bucket_name, filename, public=True, static_headers=False, gzip=False):
    bucket = get_or_create_bucket(bucket_name, cors='http://%s' % env.host_string)
    print('Uploading %s to Amazon S3 bucket %s' % (filename, bucket_name))
    k = bucket.new_key(filename)
    if static_headers:
        content_types = {
            '.js': 'application/x-javascript',
            '.map': 'application/json',
            '.json': 'application/json',
            '.css': 'text/css',
            '.html': 'text/html',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.png': 'image/png',
            '.pdf': 'application/pdf',
        }
        dir_filename, extension = os.path.splitext(filename)
        k.set_metadata('Content-Type', content_types.get(extension, 'text/plain'))
        k.set_metadata('Cache-Control', 'max-age=31536000')
        k.set_metadata('Expires', 'Thu, 31 Dec 2015 23:59:59 GM')
        if gzip:
            k.set_metadata('Content-Encoding', 'gzip')
    def percent_cb(complete, total):
        sys.stdout.write('.')
        sys.stdout.flush()
    k.set_contents_from_filename(filename, cb=percent_cb, num_cb=10)
    if public:
        k.set_acl('public-read')

# Tasks

@task
def bootstrap():
    print(red("Configuring application"))
    install('imagemagick')
    with cd(env.app_path):
        env.run('virtualenv %(env)s -p %(python)s' % dict(env=env.venv, python=env.python))
        with prefix(venv()):
            env.run('pip install -r requirements.txt')
    print(green("Bootstrap success"))

@task
def upload_common_static_files():
    print(red("Uploading common static files to S3"))
    files = ['static/common.js', 'static/common.css']
    for f in files:
        upload_file_to_s3('weblibraries', f, public=True, static_headers=True)
        if f.endswith('.js'):
            fmin, fmap = minify_js(f)
            upload_file_to_s3('weblibraries', fmin, public=True, static_headers=True)
            upload_file_to_s3('weblibraries', fmap, public=True, static_headers=True)


@task
def rename(folder='.', extension=None):
    output = '%(folder)s/output' % dict(folder=folder)
    local('rm -rf %(output)s && mkdir %(output)s' % dict(output=output))
    (_, _, filenames) = os.walk(folder).next()
    i = 1
    for filename in filenames:
        name, ext = os.path.splitext(filename)
        ext = ext.lower()
        if extension is None or extension in ext:
            newfilename = str(i).zfill(4)
            newfile = '%(output)s/%(newfilename)s%(ext)s' % dict(output=output, newfilename=newfilename, ext=ext)
            local('cp %(filename)s %(newfile)s' % dict(filename=filename, newfile=newfile))
            i += 1

@task
def convert(options, source, result):
    local('convert %(options)s %(source)s %(result)s' % dict(options=options, source=source, result=result))

@task
def convert_all(options, folder='.'):
    output = '%(folder)s/output' % dict(folder=folder)
    local('rm -rf %(output)s && mkdir %(output)s' % dict(output=output))
    (_, _, filenames) = os.walk(folder).next()
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    for filename in filenames:
        name, ext = os.path.splitext(filename)
        if ext.lower() in image_extensions:
            source = '%(folder)s/%(input)s' % dict(folder=folder, input=filename)
            result = '%(output)s/%(input)s' % dict(output=output, input=filename)
            convert(options, source, result)

@task
def resize_imgs(folder='.'):
    # convert_all('-resize 50%%')
    convert_all('-resize 1024x768')

@task
def compress_imgs(folder='.'):
    # convert_all('-strip -interlace Plane -gaussian-blur 0.05 -quality 85%')
    convert_all('-strip -interlace Plane -gaussian-blur 0.05 -quality 75%')
    # convert_all('-strip -interlace Plane -gaussian-blur 0.05 -quality 60%')
    # convert_all('-strip -interlace Plane -gaussian-blur 0.05 -quality 55%')

@task
def logos():
    local('rm -rf output && mkdir output')
    square = 'logo-1024x1024.png'
    portrait = 'logo-1024x1024.png'
    landscape = 'logo-1024x1024.png'
    banner = 'logo-1024x1024.png'

    def logo(source, sizes):
        name, ext = os.path.splitext(source)
        for size in sizes:
            convert('-resize %(size)s\!' % dict(size=size), square, 'logo-%(size)s%(ext)s' % dict(size=size, ext=ext))

    # FB logos: 512, 180, 16
    # favicon: 32, 16
    sizes = ['512x512', '180x180', '144x144', '114x114', '72x72', '57x57', '32x32', '16x16']
    logo(square, sizes)

    # Mobile Portrait
    sizes = ['1536x2008', '640x1136', '768x1004', '640x960', '320x480']
    logo(portrait, sizes)

    # Mobile Landscape
    sizes = ['2048x1496', '1024x748']
    logo(landscape, sizes)

    # Banners
    # 800x150 FB app cover image
    # 400x150 FB cover image
    # 155x100 FB app web banner
    # 200x60 Site logo
    # 150x50 PagSeguro logo
    # 150x50 Site logo
    # 140x40 Site logo
    sizes = ['800x150', '400x150', '155x100', '200x60', '150x50', '140x40']
    logo(banner, sizes)