# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/trusty64"

  config.vm.define "full-text-search-drf-vm" do |vm_define|
  end

  config.vm.hostname = "django-full-text-search-drf.local"

  config.vm.network "forwarded_port", guest: 8000, host: 8000

  config.vm.synced_folder ".", "/home/vagrant/full_text_search_drf/"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "1024"
    vb.name = "full-text-search-drf-vm"
  end

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get install -y python3 python3-dev python3.4-venv postgresql postgresql-server-dev-all

    sudo -u postgres psql --command="CREATE USER full_text_search_drf WITH PASSWORD 'full_text_search_drf';"
    sudo -u postgres psql --command="CREATE DATABASE full_text_search_drf WITH OWNER full_text_search_drf;"
    sudo -u postgres psql --command="GRANT ALL PRIVILEGES ON DATABASE full_text_search_drf TO full_text_search_drf;"
  SHELL

  config.vm.provision "shell", privileged: false, inline: <<-SHELL
    pyvenv-3.4 --without-pip full_text_search_drf_venv
    source full_text_search_drf_venv/bin/activate
    curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | python

    pip install -r full_text_search_drf/requirements.txt

    cd full_text_search_drf/full_text_search_drf/

    python manage.py migrate
    python manage.py loaddata data.json
  SHELL
end
