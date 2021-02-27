#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import json
import ovh
import sys
import requests, time

'''
API credentials
can be provided in variety of ways:
(see https://github.com/ovh/python-ovh#configuration)
-explicitly here :
'''
#client = ovh.Client(
#        endpoint           = "ovh-eu",
#        application_key    = "XXXXXXXXXXXXXXXX",
#        application_secret = "YYYYYYYYYYYYYYYY",
#        consumer_key       = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
#        )
'''
-or in the ENVIRONMENT 
-or in a ovh.conf file
in which cases we can call with no argument (the ovh module gets the credentials on its own):        
'''
client = ovh.Client() 

default_ttl =  600  # seconds 
# ttl = how long will a DNS server cache the value before checking it at the Registrar. Longer value yields faster name resolution most of the time, but less frequent updates
records_changed = 0 
# list of hosts (=subdomain.domain.tld) to update, each a dictionnary with at least "domain" and "subdomain" defined
hosts = [
        { 
            "domain": "mydomain.tld", # Required
            "subdomain": "www", # Required. Explicit subdomain or empty string "" (for @) or "*" for wildcard
            #"ipv6": any_value_except_False # Optional : maintain corresponding record, when possible
            "ipv4": False, #explicitly disable modifiying ipv4 (A) records, even if public IPV4 exists (a possibly erroneous record would be left as-is)
            #"ttl": 60 # optional : if 'ttl' in specified in host, overrides the global default value 
        },
        { 
            "domain": "otherdomain.tld",
            "subdomain": ""
            # 'ipv4' and 'ipv6' are not listed : automatically maintain any/both records, according to availability
        }
    ]

checkDNS_interval_hrs = 12.1 # when the saved IP addresses are old, check the DNS record, even if the addresses did not change
#save last known address in local file. 
current_ip_file = "/tmp/current_ip.json" 


def send_email(msg, sender = 'no_reply@mydomain.com', receiver = 'admin@mydomain.com')
  import smtplib

  try :
     smtpObj = smtplib.SMTP('localhost')
     smtpObj.sendmail(sender, receiver,
         "From: {}\nTo: {}\nSubject: DNS Update problem\n\n{}\n".format(sender, receiver, msg)
         )         
  except smtplib.SMTPException:
     print( timestamp()," : Error unable to send email")

def get_current_ip(v = 4):
    url = 'https://api6.ipify.org' if v == 6 else 'https://api.ipify.org'
    try :         
        r = requests.get(url, timeout=5.0)
    except requests.exceptions.RequestException as e:
        #print("failed getting ipv{} address because {} occurred".format(v, str(e)))
        return False
    return r.text if r.status_code == requests.codes.ok else False
    
def timestamp() :
    return time.asctime( time.localtime(time.time()) )

def update_record(domain, subdomain, new_ip, _ttl = 600):
    #Update the (A or AAAA) record with the provided IP

    typ = 'AAAA' if ":" in new_ip else 'A'
    #print("checking record {} for {}.{}".format(typ,subdomain,domain))
    path = "/domain/zone/{}/record".format(domain)
    result = client.get(path,
                        fieldType = typ,
                        subDomain = subdomain
                     )

    if len(result) != 1:
        #creating NEW record
        result = client.post(path,
                    fieldType = typ,
                    subDomain = subdomain,
                    target = new_ip,
                    ttl = _ttl
                     )
        client.post('/domain/zone/{}/refresh'.format(domain))
        result = client.get(path,
                        fieldType=typ,
                        subDomain=subdomain
                        )
        record_id = result[0]
        records_changed += 1
        print("{} : ### created new record {} for {}.{}".format(timestamp(),typ,subdomain,domain))
    else :
        # record exists
        record_id = result[0]
        path = "/domain/zone/{}/record/{}".format(domain,record_id)
        result = client.get(path)
        oldip = result['target']
        #print('record exists, with ip :',oldip)
        if oldip == new_ip :
            #print('nothing to do')
            return
        else :
            #print('updating to ', new_ip)
            result = client.put(path, 
                subDomain = subdomain, 
                target = new_ip, 
                ttl = _ttl
                 )
            client.post('/domain/zone/{}/refresh'.format(domain))
            records_changed += 1
    #checking changes
    result = client.get("/domain/zone/{}/record/{}".format(domain,record_id))
    if new_ip != result['target'] :
        records_changed -= 1
        raise Exception("Error updating {}.{} with {}".format(subdomain,domain,new_ip))
        
        
def delete_record(domain, subdomain, typ):
    """
    if it exists, delete an A or AAAA record  
    (because the corresponding IP is not available)
    """
    #print("checking record {} for {}.{}".format(typ,subdomain,domain))
    result = client.get("/domain/zone/{}/record".format(domain),
                        fieldType = typ,
                        subDomain = subdomain
                     )
    if len(result) == 1:
        # record exists, delete it
        record_id = result[0]
        print("{} : ### deleting record {} for {}.{}".format(timestamp(),typ,subdomain,domain))
        client.delete("/domain/zone/{}/record/{}".format(domain,record_id))
        client.post('/domain/zone/{}/refresh'.format(domain))
        records_changed += 1


#reload saved values
try:
    with open(current_ip_file, 'r') as f:
        old_time, old_ipv4, old_ipv6   = json.load(f)
except IOError:
    #print("No old ips recorded")
    pass

current_ipv4 = get_current_ip(4)
current_ipv6 = get_current_ip(6)
#print('current ips: {} ; {}'.format(current_ipv4, current_ipv6))

if current_ipv4 or current_ipv6 : #we could get at least one address
  try :
    need_update = (old_ipv4 != current_ipv4) or (old_ipv6 != current_ipv6) or ((old_time - time.time()) > 3600.0 * checkDNS_interval_hrs)
  except : #old values do not exist, we must check the records
    need_update = True 
  if need_update :
    try :
      for host in hosts :
        domain = host["domain"]
        subdomain = host ["subdomain"]
        if ('ipv4' not in host) or (host['ipv4'] != False) :
            if current_ipv4 :
                ttl = default_ttl if ('ttl' not in host) else host['ttl']
                update_record(domain, subdomain, current_ipv4, _ttl = ttl)
            else :
                delete_record(domain, subdomain, 'A')
        else :
            #print("Not touching A record for {}.{}, as instructed".format(subdomain, domain))
            pass
        if ('ipv6' not in host) or (host['ipv6'] != False) :
            if current_ipv6 :
                ttl = default_ttl if ('ttl' not in host) else host['ttl']
                update_record(domain, subdomain, current_ipv6, _ttl = ttl)
            else :
                delete_record(domain, subdomain, 'AAAA')
        else :
            #print("Not touching AAAA record for {}.{}, as instructed".format(subdomain, domain))
            pass
      #all hosts records have been updated without errors, log change and save current addresses
      print("{} : new addresses {} ; {} -- {} records updates".format(timestamp(), current_ipv4, current_ipv6, records_changed)    
      with open(current_ip_file, 'w') as f:
        json.dump([time.time(), current_ipv4, current_ipv6],f)
    except Exception as e: #some error occured (API down, keys expired...?),
      msg = "{} : ### error {} while updating records!! {} records updated with new addresses {} ; {}".format(timestamp(),  str(e), records_changed, current_ipv4, current_ipv6)
      print(msg)
      send_email(msg)
      # not saving new addresses, so that update is attempted again.
  else :
    #print("nothing to do!")
    pass
else :
  msg = "{} : cannot get IPs. Network down? ipify.org down?".format(timestamp())
  print(msg)
  send_email(msg)



