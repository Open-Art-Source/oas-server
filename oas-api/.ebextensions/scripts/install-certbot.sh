#!/bin/bash
cert_type=$(/opt/elasticbeanstalk/bin/get-config environment -k CERT_TYPE)
cert_email=$(/opt/elasticbeanstalk/bin/get-config environment -k CERT_EMAIL)
cert_domain=$(/opt/elasticbeanstalk/bin/get-config environment -k CERT_DOMAIN)

if [[ "$cert_type" == "None" ]] || [[ "$cert_type" == "" ]]; then
   echo "do not install ssl cert, use stub cert"
   cp -a .ebextensions/platform/options-ssl-nginx.conf /etc/letsencrypt/
   cp -a .ebextensions/platform/ssl-dhparams.pem /etc/letsencrypt/
   #cp -a .platform/nginx/conf.d/http-https-proxy.conf /etc/nginx/conf.d/
   exit 0
fi
if [[ "$cert_type" != "production" ]]; then
# !! --test-cert: REMOVE FOR PRODUCTION, use the staging server for the certificate !!
staging=--test-cert
fi
#wait for firewall(30s) when it is brand new instance start
echo "waiting for 45s for aws ec2 startup delay"
sleep 45
certbot $staging --debug --non-interactive --redirect --agree-tos --nginx --email ${cert_email} --domains ${cert_domain} --keep-until-expiring
#if [[ $? -eq 0 ]] && [[ -e /etc/letsencrypt/live/${cert_domain} ]]; then
if [[ -e /etc/letsencrypt/live/${cert_domain} ]]; then
#only do setup if certbot has no error and created the cert
#remove stub files
#[[ ! -e /etc/letsencrypt/accounts ]] && rm -rf /etc/letsencrypt/acme.local 
#make the modified http-https-proxy.conf listen on 80/443(certbot make it 443 only which is not good for behind ALB
grep -E "listen 80;" /etc/nginx/conf.d/http-https-proxy.conf || sed -i 's/listen 443 ssl;/listen 80; listen 443 ssl;/' /etc/nginx/conf.d/http-https-proxy.conf
#enable ssl redirection
sed -i 's/set \$ssl N;/set $ssl Y; #changed by install script/' /etc/nginx/conf.d/http-https-proxy.conf
#4. make a copy of the modified .conf to platform(disappeared after deploy !!, restore via postdeploy hook)
#mkdir -p /tmp/nginx/conf.d && cp -a /etc/nginx/conf.d/http-https-proxy.conf /tmp/nginx/conf.d/
#5 also save it to /tmp, urber important
cp -a /etc/nginx/conf.d/http-https-proxy.conf /tmp/  
[[ -e /etc/letsencrypt/live/${cert_domain} ]] && ln -nsf ${cert_domain} /etc/letsencrypt/live/default
[[ -e /etc/letsencrypt/live/${cert_domain} ]] && cp -a /etc/letsencrypt/live/${cert_domain}/* /etc/letsencrypt/live/acme.local/
fi
