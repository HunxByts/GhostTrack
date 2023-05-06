#!/usr/bin/python
# << CODE BY HUNX04
# << MAU RECODE ??? IZIN DULU LAH,  MINIMAL TAG AKUN GITHUB MIMIN YANG MENGARAH KE AKUN INI, LEBIH GAMPANG SI PAKE FORK
# << KALAU DI ATAS TIDAK DI IKUTI MAKA AKAN MENDAPATKAN DOSA KARENA MIMIN GAK IKHLAS
# “Wahai orang-orang yang beriman! Janganlah kamu saling memakan harta sesamamu dengan jalan yang batil,” (QS. An Nisaa': 29). Rasulullah SAW juga melarang umatnya untuk mengambil hak orang lain tanpa izin.

#IMPORT MODULE

import json
import requests
import time
import os
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from sys import stderr


Bl='\033[30m' # VARIABLE BUAT WARNA CUYY
Re='\033[1;31m'
Gr='\033[1;32m'
Ye='\033[1;33m'
Blu='\033[1;34m'
Mage='\033[1;35m'
Cy='\033[1;36m'
Wh='\033[1;37m'

#BANNER TOOLS
os.system('clear')
stderr.writelines(f"""{Gr}
   ________               __      ______                __  
  / ____/ /_  ____  _____/ /_    /_  __/________ ______/ /__
 / / __/ __ \/ __ \/ ___/ __/_____/ / / ___/ __ `/ ___/ //_/
/ /_/ / / / / /_/ (__  ) /_/_____/ / / /  / /_/ / /__/ ,<   
\____/_/ /_/\____/____/\__/     /_/ /_/   \__,_/\___/_/|_| 

          {Wh}[ + ]  C O D E   B Y  H U N X  [ + ]  
        
    {Wh}[ 1 ] {Gr}IP Tracker
    {Wh}[ 2 ] {Gr}Show Your IP
    {Wh}[ 3 ] {Gr}Phone Tracker
    {Wh}[ 4 ] {Gr}Username Tracker
    {Wh}[ 0 ] {Gr}Exit
""")

input_user = input(f'\n   {Wh}@Ghost~# {Gr}') #OPSI MENU


if input_user == '1': #OPSI 1
    os.system('clear')
    time.sleep(1)
    stderr.writelines(f"""{Wh}
     .-.
   .'   `.          {Wh}--------------------------------
   :g g   :         {Wh}| {Gr}GHOST - TRACKER - IP ADDRESS {Wh}|
   : o    `.        {Wh}|       {Gr}@CODE BY HUNXBYTS      {Wh}|
  :         ``.     {Wh}--------------------------------
 :             `.
:  :         .   `.
:   :          ` . `.
 `.. :            `. ``;
    `:;             `:'
       :              `.
        `.              `.     .
          `'`'`'`---..,___`;.-'
    """)

    try:
        def IP_Track():
            ip = input(f"{Wh}\n Enter IP target : {Gr}") #INPUT IP ADDRESS
            print()
            print(f' {Wh}============= {Gr}SHOW INFORMATION IP ADDRESS {Wh}=============')
            req_api = requests.get(f"http://ipwho.is/{ip}") #API IPWHOIS.IS
            ip_data = json.loads(req_api.text)
            time.sleep(2)
            print(f"{Wh}\n IP target       :{Gr}", ip)
            print(f"{Wh} Type IP         :{Gr}", ip_data["type"])
            print(f"{Wh} Country         :{Gr}", ip_data["country"])
            print(f"{Wh} Country Code    :{Gr}", ip_data["country_code"])
            print(f"{Wh} City            :{Gr}", ip_data["city"])
            print(f"{Wh} Continent       :{Gr}", ip_data["continent"])
            print(f"{Wh} Continent Code  :{Gr}", ip_data["continent_code"])
            print(f"{Wh} Region          :{Gr}", ip_data["region"])
            print(f"{Wh} Region Code     :{Gr}", ip_data["region_code"])
            print(f"{Wh} Latitude        :{Gr}", ip_data["latitude"])
            print(f"{Wh} Longitude       :{Gr}", ip_data["longitude"])
            lat = int(ip_data['latitude'])
            lon = int(ip_data['longitude'])
            print(f"{Wh} Maps            :{Gr}",f"https://www.google.com/maps/@{lat},{lon},8z")
            print(f"{Wh} EU              :{Gr}", ip_data["is_eu"])
            print(f"{Wh} Postal          :{Gr}", ip_data["postal"])
            print(f"{Wh} Calling Code    :{Gr}", ip_data["calling_code"])
            print(f"{Wh} Capital         :{Gr}", ip_data["capital"])
            print(f"{Wh} Borders         :{Gr}", ip_data["borders"])
            print(f"{Wh} Country Flag    :{Gr}", ip_data["flag"]["emoji"])
            print(f"{Wh} ASN             :{Gr}", ip_data["connection"]["asn"])
            print(f"{Wh} ORG             :{Gr}", ip_data["connection"]["org"])
            print(f"{Wh} ISP             :{Gr}", ip_data["connection"]["isp"])
            print(f"{Wh} Domain          :{Gr}", ip_data["connection"]["domain"])
            print(f"{Wh} ID              :{Gr}", ip_data["timezone"]["id"])
            print(f"{Wh} ABBR            :{Gr}", ip_data["timezone"]["abbr"])
            print(f"{Wh} DST             :{Gr}", ip_data["timezone"]["is_dst"])
            print(f"{Wh} Offset          :{Gr}", ip_data["timezone"]["offset"])
            print(f"{Wh} UTC             :{Gr}", ip_data["timezone"]["utc"])
            print(f"{Wh} Current Time    :{Gr}", ip_data["timezone"]["current_time"])
        if __name__ == '__main__':
            IP_Track()
    except KeyboardInterrupt:
        print(f" {Wh}[{Ye}!{Wh}] {Ye}PROGRAM STOPPED...")

elif input_user == '3': #OPSI 2
    os.system('clear')
    time.sleep(1)
    stderr.writelines(f"""{Wh}
     .-.
   .'   `.          {Wh}----------------------------------
   :g g   :         {Wh}| {Gr}GHOST - TRACKER - PHONE NUMBER {Wh}|
   : o    `.        {Wh}|        {Gr}@CODE BY HUNXBYTS       {Wh}|
  :         ``.     {Wh}----------------------------------
 :             `.
:  :         .   `.
:   :          ` . `.
 `.. :            `. ``;
    `:;             `:'
       :              `.
        `.              `.     .
          `'`'`'`---..,___`;.-'
    """)

    try:
        def phoneGW():
            User_phone = input(f"\n {Wh}Enter phone number target {Gr}Ex [+6281xxxxxxxxx] {Wh}: {Gr}") #INPUT NUMBER PHONE
            default_region = "ID" #DEFAULT NEGARA INDONESIA

            parsed_number = phonenumbers.parse(User_phone, default_region) # VARIABLE PHONENUMBERS
            region_code = phonenumbers.region_code_for_number(parsed_number)
            jenis_provider = carrier.name_for_number(parsed_number, "en")
            location = geocoder.description_for_number(parsed_number, "id")
            is_valid_number = phonenumbers.is_valid_number(parsed_number)
            is_possible_number = phonenumbers.is_possible_number(parsed_number)
            formatted_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            formatted_number_for_mobile = phonenumbers.format_number_for_mobile_dialing(parsed_number, default_region, with_formatting=True)
            number_type = phonenumbers.number_type(parsed_number)
            timezone1 = timezone.time_zones_for_number(parsed_number)
            timezoneF = ', '.join(timezone1)

            print(f"\n {Wh}========== {Gr}SHOW INFORMATION PHONE NUMBERS {Wh}==========")
            print(f"\n {Wh}Location             :{Gr} {location}")
            print(f" {Wh}Region Code          :{Gr} {region_code}")
            print(f" {Wh}Timezone             :{Gr} {timezoneF}")
            print(f" {Wh}Operator             :{Gr} {jenis_provider}")
            print(f" {Wh}Valid number         :{Gr} {is_valid_number}")
            print(f" {Wh}Possible number      :{Gr} {is_possible_number}")
            print(f" {Wh}International format :{Gr} {formatted_number}")
            print(f" {Wh}Mobile format        :{Gr} {formatted_number_for_mobile}")
            print(f" {Wh}Original number      :{Gr} {parsed_number.national_number}")
            print(f" {Wh}E.164 format         :{Gr} {phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)}")
            print(f" {Wh}Country code         :{Gr} {parsed_number.country_code}")
            print(f" {Wh}Local number         :{Gr} {parsed_number.national_number}")
            if number_type == phonenumbers.PhoneNumberType.MOBILE:
                print(f" {Wh}Type                 :{Gr} This is a mobile number")
            elif number_type == phonenumbers.PhoneNumberType.FIXED_LINE:
                print(f" {Wh}Type                 :{Gr} This is a fixed-line number")
            else:
                print(f" {Wh}Type                 :{Gr} This is another type of number")
        if __name__ == '__main__':
            phoneGW()
    except KeyboardInterrupt:
        print(f" {Wh}[{Ye}!{Wh}] {Ye}PROGRAM STOPPED...")
    
elif input_user == '2': #OPSI 3
    os.system('clear')
    time.sleep(1)
    stderr.writelines(f"""{Wh}
     .-.
   .'   `.          {Wh}----------------------------------
   :g g   :         {Wh}|  {Gr}GHOST - SHOW YOUR IP ADDRESS  {Wh}|
   : o    `.        {Wh}|        {Gr}@CODE BY HUNXBYTS       {Wh}|
  :         ``.     {Wh}----------------------------------
 :             `.
:  :         .   `.
:   :          ` . `.
 `.. :            `. ``;
    `:;             `:'
       :              `.
        `.              `.     .
          `'`'`'---..,___`;.-'
""")

    try:
        def showIP():
            respone = requests.get('https://api.ipify.org/')
            Show_IP = respone.text
            
            print(f"\n {Wh}========== {Gr}SHOW INFORMATION YOUR IP {Wh}==========")
            print(f"\n {Wh}[{Gr} + {Wh}] Your IP Adrress : {Gr}{Show_IP}")
            print(f"\n {Wh}==============================================")
        if __name__ == '__main__':
            showIP()
    except KeyboardInterrupt:
        print(f" {Wh}[{Ye}!{Wh}] {Ye}PROGRAM STOPPED...")



elif input_user == '4':
    os.system('clear')
    time.sleep(1)
    stderr.writelines(f"""{Wh}
     .-.
   .'   `.          {Wh}----------------------------------
   :g g   :         {Wh}|    {Gr}GHOST - TRACKER USERNAME    {Wh}|
   : o    `.        {Wh}|        {Gr}@CODE BY HUNXBYTS       {Wh}|
  :         ``.     {Wh}----------------------------------
 :             `.
:  :         .   `.
:   :          ` . `.
 `.. :            `. ``;
    `:;             `:'
       :              `.
        `.              `.     .
          `'`'`'---..,___`;.-'
""")
    try:
        def TrackLu(username):
            results = {}
            social_media = [
            {"url": "https://www.facebook.com/{}", "name": "Facebook"},
            {"url": "https://www.twitter.com/{}", "name": "Twitter"},
            {"url": "https://www.instagram.com/{}", "name": "Instagram"},
            {"url": "https://www.linkedin.com/in/{}", "name": "LinkedIn"},
            {"url": "https://www.github.com/{}", "name": "GitHub"},
            {"url": "https://www.pinterest.com/{}", "name": "Pinterest"},
            {"url": "https://www.tumblr.com/{}", "name": "Tumblr"},
            {"url": "https://www.youtube.com/{}", "name": "Youtube"},
            {"url": "https://soundcloud.com/{}", "name": "SoundCloud"},
            {"url": "https://www.snapchat.com/add/{}", "name": "Snapchat"},
            {"url": "https://www.tiktok.com/@{}", "name": "TikTok"},
            {"url": "https://www.behance.net/{}", "name": "Behance"},
            {"url": "https://www.medium.com/@{}", "name": "Medium"},
            {"url": "https://www.quora.com/profile/{}", "name": "Quora"},
            {"url": "https://www.flickr.com/people/{}", "name": "Flickr"},
            {"url": "https://www.periscope.tv/{}", "name": "Periscope"},
            {"url": "https://www.twitch.tv/{}", "name": "Twitch"},
            {"url": "https://www.dribbble.com/{}", "name": "Dribbble"},
            {"url": "https://www.stumbleupon.com/stumbler/{}", "name": "StumbleUpon"},
            {"url": "https://www.ello.co/{}", "name": "Ello"},
            {"url": "https://www.producthunt.com/@{}", "name": "Product Hunt"},
            {"url": "https://www.snapchat.com/add/{}", "name": "Snapchat"},
            {"url": "https://www.telegram.me/{}", "name": "Telegram"},
            {"url": "https://www.weheartit.com/{}", "name": "We Heart It"}
            ]

            for site in social_media:
                url = site['url'].format(username)
                response = requests.get(url)
                if response.status_code == 200:
                    results[site['name']] = url
                else:
                    results[site['name']] = (f"{Ye}Username not found {Ye}!")
            return results
        username = input(f"\n {Wh}Enter Username : {Gr}")
        print(f"\n {Wh}========== {Gr}SHOW INFORMATION USERNAME {Wh}==========")
        print()
        results = TrackLu(username)
        for site, url in results.items():
            print(f" {Wh}[ {Gr}+ {Wh}] {site} : {Gr}{url}")
    except KeyboardInterrupt:
        print(f" {Wh}[{Ye}!{Wh}] {Ye}PROGRAM STOPPED...")

elif input_user == '0':
    print(f"\n  {Wh}[{Ye}!{Wh}] {Ye}THANK'S FOR USING TOOL {Ye}GHOST-TRACK !")
else:
    print(f" {Ye}Opss no option !") #FALSE

