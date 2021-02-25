# ovh-dns-updater
simple python script to update A/AAAA DNS records at OVH registrar 


This script can maintain the A and/or AAAA DNS records (*)
of all your domains and subdomains hosted on the machine 
running this script, using OVH API. It is especially usefull it you are self-hosting and have only
a semi-permanent IP address with your ISP.

(* The script handles IPV4 and/or IPV6 addressing, given what
is available)

### Why yet another script for doing that?

There are tons of solutions for updating DNS records out there, and even pretty good ones.
For instance one could use this [dns updater](https://github.com/qdm12/ddns-updater),
or this [ddclient](https://github.com/ddclient/ddclient) dyndns client. So why coming up with my own?

Well, OVH's DynHost method that ddclient uses is badly crippled, as it cannnot:
- do multiple domain/subdomains with a single id set 
  (OVH's Dynhost requires separate logins per subdomain!).
- update AAAA records if you have ivp6 enabled 
  (OVH's DynHost supports ipv4 only).
  
And all OVH-API scripts I could find were not filling the bill for me. They are either unsuited or too heavy, complex universal tools.
For this task, I prefer a simple, easy to understand script that does little and that I can easily modify when needed.

If you have already created DynHost records in OVH, remove them before
 using that script. -- alternatively, you can modify the script to
 update dynhost records, if you prefer.

## What this script does

The script queries the current *public* IP addresses
(V4 and V6) and checks the DNS A/AAAA records at OVH for all
domain/subdomains hosted on the machine (list defined as a dictionary in the script). 

If needed, the record is updated or created (You can add a new
subdomain this way).

If either IPV4 or IPV6 address is not available but the corresponding
DNS record nevertheless exists, it is suppressed (Otherwise your site
will be unreachable with this ip version). Such situation presumably
arises because you disabled that ip version in your box (or your new
ISP does not offer it)

Optionally, updating an IP addressing mode (4 or 6) can be disabled for
any given domain/subdomain (for intance, if you want it accessible
 _only_ in IPV4).

## Setting up

this script needs extra modules:
`pip install ovh requests`

In order to acccess the OVH API from this script, 
you need to generate API access keys 
at this site [https://eu.api.ovh.com/createToken/](https://eu.api.ovh.com/createToken/)  
(or use another access point relevant for your OVH subscription)

Provide your OVH login and password, a script name, a purpose,
a validity duration for the keys and ask for the four permissions:
```
GET /domain/zone/*
PUT /domain/zone/*
POST /domain/zone/*
DELETE /domain/zone/*
```
This will allow the script to
- read the statuses of your domains/subdomains (GET)
- update records (PUT)
- create inexistent records and refresh (POST)
- delete record if the ipv6 or ipv4 address no longer exists

The keys delievered should be inserted in the script.
