#-*- coding: utf-8 -*-
#!/usr/bin/python
'''
Created on 2015/08/13

@author: Administrator
'''

from models import app_user,application
from utils import sftp2,ssh2_deploy
import logging

from datetime import datetime
today = (datetime.now().date()).strftime('%Y-%m-%d')

def tomcat_deploy(data_req):
    
    data_txt_web = []
    data_txt_app = []
    
    for data in data_req:
        hostname = data['host_name']
        username = data['username']
    
        if('web' in hostname):
            web_index = username.index('web')
            module = username[0:web_index] + '-' + username[web_index:]
            password = app_user.objects.all().filter(host_id=data['host_id'],username=data['username']).values('password')[0]['password']            
            data_txt_web.append({'host_id':data['host_id'],'hostname':hostname,'area':data['area'],'ip':data['ip'],'username':username,'password':password,'module':module,'instance':data['instance'],'primary':'','version_num':data['version_num']})
        elif('app' in hostname):
            app_index = username.index('app')
            module = username[0:app_index] + '-' + username[app_index:]            
            password = app_user.objects.all().filter(host_id=data['host_id'],username=data['username']).values('password')[0]['password']
            data_txt_app.append({'host_id':data['host_id'],'hostname':hostname,'area':data['area'],'ip':data['ip'],'username':username,'password':password,'module':module,'instance':data['instance'],'primary':'','version_num':data['version_num']})
    
    '''
        cloudops step:
        1.write text file
        2.copy file to cloudops host
        3.excute shell scripts  
    '''
    #web server
    web_server_count = len(data_txt_web)
    if (web_server_count > 0):
        for i in range(web_server_count):
            if('01' in data_txt_web[i]['area']):
                cmd = r''
                for info in data_txt_web:
                    cmd = cmd + info['area'] + ' ' + info['ip'] + ' ' +info['username']+ ' ' + info['password'] + ' '  + info['module'] + ' ' + info['instance'] + ' '+ info['version_num']  +' \\n'
              
                cmd = cmd[:-2]
                cmd = r'cd /app/'+data_txt_web[i]['username']+'/;echo "'+ cmd + '" > data.txt'                
               
                #set primary host for cloudops
                data_txt_web[i]['primary'] = 'primary'
                #var 
                host_ip = data_txt_web[i]['ip']
                username = data_txt_web[i]['username']
                password = data_txt_web[i]['password']
                module = data_txt_web[i]['module']
                
                application.objects.create(host_id=data_txt_web[i]['host_id'],area=data_txt_web[i]['area'],middleware='tomcat',module=module,username=username,version_num=data_txt_web[i]['version_num'],instance_num=data_txt_web[i]['instance'],primary='primary',create_date=today,status='deployed')

                #write data text
                ssh2_deploy(host_ip,username,password,cmd)
                #put template file to target host
                sftp2(host_ip,username,password,'/app/tmt/tomcat.tar','/app/'+username+'/tomcat.tar')
                #tar xvf file name and run 3 scripts
                cmd_deploy_step1 = r'cd /app/'+username+';tar xf tomcat.tar;sh 01_startdoc.sh >>cloudops.log;'\
                             'sh 02_mvserver.sh >>cloudops.log;'
                
                ssh2_deploy(host_ip,username,password,cmd_deploy_step1)
                    
                 
    #app server
    app_server_count = len(data_txt_app)
    if ( app_server_count > 0):
        for i in range(app_server_count):
            if('01' in data_txt_app[i]['area']):
                cmd = ''
                for info in data_txt_app:
                    cmd = cmd + info['area'] + ' ' + info['ip'] + ' ' +info['username']+ ' ' + info['password'] + ' '  + info['module'] + ' ' + info['instance'] +' '+info['version_num'] +' \\n'
                cmd = r'cd /app/'+data_txt_app[i]['username']+';echo "'+ cmd + ' " > data.txt' 
                #set primary host for cloudops
                data_txt_app[i]['primary'] = 'primary'                
                
                #var 
                host_ip = data_txt_app[i]['ip']
                username = data_txt_app[i]['username']
                password = data_txt_app[i]['password']
                module = data_txt_app[i]['module']
                
                application.objects.create(host_id=data_txt_app[i]['host_id'],area=data_txt_app[i]['area'],middleware='tomcat',module=module,username=username,version_num=data_txt_app[i]['version_num'],instance_num=data_txt_app[i]['instance'],primary='primary',create_date=today,status='deployed')
            
                #write data text
                ssh2_deploy(host_ip,username,password,cmd)
                #put template file to target host
                sftp2(host_ip,username,password,'/app/tmt/tomcat.tar','/app/'+username+'/tomcat.tar')
                
                cmd_deploy_step1 = r'cd /app/'+username+';tar xf tomcat.tar;sh 01_startdoc.sh >>cloudops.log;'\
                             'sh 02_mvserver.sh >>cloudops.log;'

                ssh2_deploy(host_ip,username,password,cmd_deploy_step1)
                    
                                      
            
    logging.info(data_txt_web)
    logging.info(data_txt_app)
    data_txt = data_txt_web + data_txt_app
    logging.info(data_txt)
    #input database application
    app_data = []
     
    for deploy_info in data_txt:
        if(not deploy_info['primary']):
            app_data.append(application(host_id=deploy_info['host_id'],area=deploy_info['area'],middleware='tomcat',module=deploy_info['module'],username=deploy_info['username'],version_num=deploy_info['version_num'],instance_num=deploy_info['instance'],primary=deploy_info['primary'],create_date=today,status='deployed'))
    application.objects.bulk_create(app_data)
    
    #run startup scripts and check the cloudops status    