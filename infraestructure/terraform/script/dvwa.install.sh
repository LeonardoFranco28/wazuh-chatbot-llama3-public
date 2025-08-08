#!/bin/bash

set -e  # Exit on error

# Update packages
apt update

# Install required packages
apt-get -y install apache2 mariadb-server php php-mysqli php-gd libapache2-mod-php git unzip

# Determine PHP version
PHP_VERSION=$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')

# Create DVWA database and user
mysql -e "CREATE DATABASE dvwa;"
mysql -e "CREATE USER 'dvwa'@'localhost' IDENTIFIED BY 'p@ssw0rd';"
mysql -e "GRANT ALL PRIVILEGES ON dvwa.* TO 'dvwa'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# Deploy DVWA
cd /var/www/html
rm -f index.html
git clone https://github.com/digininja/DVWA.git .
cp config/config.inc.php.dist config/config.inc.php

# Create missing directories/files
mkdir -p external/phpids/0.6/lib/IDS/tmp/
touch external/phpids/0.6/lib/IDS/tmp/phpids_log.txt

# Set ownership
chown -R www-data:www-data /var/www/html/hackable/uploads/
chown -R www-data:www-data external/phpids/0.6/lib/IDS/tmp/phpids_log.txt
chown -R www-data:www-data /var/www/html/config

# Update PHP settings
PHP_INI="/etc/php/${PHP_VERSION}/apache2/php.ini"
if [ -f "$PHP_INI" ]; then
    sed -i 's/allow_url_include = Off/allow_url_include = On/' "$PHP_INI"
else
    echo "PHP config file not found: $PHP_INI"
    exit 1
fi

# Suppress Apache ServerName warning
echo "ServerName localhost" >> /etc/apache2/apache2.conf

# Restart Apache
systemctl restart apache2

echo "DVWA installation complete!"
