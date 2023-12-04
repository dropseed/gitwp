#!/bin/sh
openssl x509 -req -in fhd_wildcard.csr -CA fhd_ca.crt -CAkey fhd_ca.key -CAcreateserial -out fhd_wildcard.crt -days 500 -sha256 -extfile v3.ext
cp fhd_wildcard.crt ../dockerfiles/proxy/certs/
