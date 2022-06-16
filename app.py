from asyncio.windows_events import NULL
from doctest import SKIP
import os
from unittest import skip
from pymongo import MongoClient
import base64
import datetime
from datetime import date
from flask import Flask, redirect, render_template, Response,request,stream_with_context,jsonify,render_template, url_for,session
import urllib
import urllib.request
import json
from datetime import timedelta
import time
import pymongo
from bson.objectid import ObjectId
import dns.resolver
from pprint import pprint
import io
import bcrypt
from flask import Flask
from flask_talisman import Talisman
import mimetypes
from flask_wtf.csrf import CSRFProtect
from typing import Any, Callable, Dict, List, Optional, Type, TYPE_CHECKING, Union
from wsgiref.simple_server import ServerHandler
ServerHandler.server_software = "Fake Server Name Here"
OVERRIDE_HTTP_HEADERS: Dict[str, Any] = {"Server":None}
mimetypes.add_type('application/javascript', '.js')
#SESSION_COOKIE_SECURE = True

mongo_url = "mongodb+srv://mayurigh:"+ urllib.parse.quote("mayuri")+"@proctoring.20kxe.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
#mongo_url="mongodb://localhost:27017"
cluster = MongoClient(mongo_url)

db = cluster["ProctoringAPI_DB"]
app = Flask(__name__)
app.config["SECRET_KEY"]="secret"
csp = {
    'default-src': '\'self\'',
    'script-src': '\'self\'',
    'script-src-attr':  '\'unsafe-inline\'',
    'script-src-elem':  '\'self\'',
    'img-src': ["'self'", 'https: data:']
}
Talisman(app,content_security_policy=csp,strict_transport_security_preload=True)
csrf = CSRFProtect(app)

@app.after_request
def apply_caching(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response

@app.after_request
def remove_header(response):
     del response.headers['X-Some-Custom-Header']
     return response
#app.permanent_session_lifetime = timedelta(minutes=20)

@app.route("/",methods=["GET"])
def x():
    x={"data":"This is just to check Network errors, please remove this API once all the changes are done"}
    return json.dumps(x)#HTTPResponse()


@app.route("/login.html",methods=["GET"])
def login():
    session.pop('logged_in_user_role', None)
    return render_template("login.html") 

@app.route("/logincheck" ,methods=["POST"])
def logincheck():
    global username
    username=request.form["username"]
    form_password=request.form["password"]
    form_password=base64.b64decode(form_password)
    form_password=form_password.decode('UTF-8') 
    input_password=form_password.encode("utf-8")
    user_details=db.my_master.find_one({"user_name":username},{"facial_img":0})
    def user(username):
        global user_data,user_role,agent_names,user_project
        user_data=list(db["my_collection"].find({"user_name":str(username)},{"role":1}))
        user_role=user_data[0]["role"]
        if user_data[0]["role"]=="supervisor":
            user_data=list(db["my_collection"].find({"user_name":str(username)},{"project_name":1,"role":1}))
            user_project=user_data[0]["project_name"]
            x=list(db.my_collection.find({"project_name":user_project,"role":"agent"},{"user_name":1,"_id":0}))
            agent_names=[]
            for i in range(0,len(x)):
                agent_names.append(x[i]["user_name"])
            user_data[0]["agent_names"]=agent_names
            session["agent_names"]=agent_names
            session["user_project"]=user_project
        return user_data[0]
    if user_details:
        session["user_name"]=username
        user(username)
        password=user_details["password"]
        if bcrypt.checkpw(input_password,password):
            session.permanent = True
            user_id=user_details["user_id"]
            global role
            role = user_details["role"]
            session['logged_in_user_role'] = role 
            session['logged_in_user_id'] = username              
            if db.my_master.find_one({"user_id":user_id,"role":"supervisor"}):
                data={"Status":"Success"}
                return json.dumps(data)
            elif db.my_master.find_one({"user_id":user_id,"role":"super admin"}):
                data={"Status":"Success"}
                return json.dumps(data)
            else:
                data={"Status":"Error","Msg":"Agents dont have access to this"}
                return json.dumps(data)
        else:
            data={"Status":"Error","Msg":"Invalid username or password"}
            return json.dumps(data)
           
    else:
        data={"Status":"Error","Msg":"Invalid username or password"}
        return json.dumps(data)                   

#get the list of projects with supervisors and agents
@app.route("/index.html",methods = ['POST', 'GET'])
def project_list():
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired.Please login again.")
    
    project_id_list = list(db["my_collection"].distinct("project_id"))
    project_list=[]
    for i in project_id_list:
        project_list.append(list(db["my_collection"].find({"project_id":i},{"_id":0,"project_id":1,"user_name":1,"project_name":1,"role":1,"initials":1})))
    def projects(project):
        data={}
        agent_list=[]
        supervisor_list = []
        agentid_list=["1","2","3","4"]
        for i in project:
            if i["role"]=="supervisor":
                data["supervisor"]=i["user_name"]
                supervisor_list.append(i["initials"])
            if i["role"]=="agent":
                agent_list.append(i["initials"])
            data["project_id"]=i["project_id"]
            data["project_name"]=i["project_name"]
            data["agent"] = agent_list
            data["supervisorlist"] = supervisor_list
            data["agentid"] = agentid_list
            data["number_of_agents"]=len(data["agent"])
        return data
    final_data=[]
    for i in project_list:
        final_data.append(projects(i))
    if session['logged_in_user_role']=="supervisor":
        final_data=list(filter(lambda x: x["supervisor"] ==session["user_name"], final_data))
    else:
        final_data=final_data
    #print(final_data)
    # return json.dumps(final_data, indent=2)
    return render_template("index.html", data=final_data)

@app.route("/ProjectListData/<PageNo>",methods = ['GET'])
def ProjectListData(PageNo):
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired.Please login again.")
    limit=4
    if(PageNo == "1"):
        offset=((int(PageNo)) * limit) - limit
    else:
         offset=((int(PageNo)) * limit) - limit
    #print(offset)
    project_id_list = list(db["my_collection"].distinct("project_id"))
    project_id_list=project_id_list[offset:offset+limit]
    project_list=[]
    for i in project_id_list:
        project_list.append(list(db["my_collection"].find({"project_id":i},{"_id":0,"project_id":1,"user_name":1,\
            "project_name":1,"role":1,"initials":1})))
    def projects(project):
        data={}
        agent_list=[]
        supervisor_list = []
        agentid_list=["1","2","3","4"]
        for i in project:
            if i["role"]=="supervisor":
                data["supervisor"]=i["user_name"]
                supervisor_list.append(i["initials"])
            if i["role"]=="agent":
                agent_list.append(i["initials"])
            data["project_id"]=i["project_id"]
            data["project_name"]=i["project_name"]
            data["agent"] = agent_list
            data["supervisorlist"] = supervisor_list
            data["agentid"] = agentid_list
            data["number_of_agents"]=len(data["agent"])
        return data
    final_data=[]
    for i in project_list:
        final_data.append(projects(i))
    if session['logged_in_user_role']=="supervisor":
        final_data=list(filter(lambda x: x["supervisor"] ==session["user_name"], final_data))
    else:
        final_data=final_data
    return json.dumps(final_data, indent=2)
    


def login_user(role,username):
    project_id_list = list(db["my_collection"].distinct("project_id"))
    project_list=[]
    for i in project_id_list:
        project_list.append(list(db["my_collection"].find({"project_id":i},{"_id":0,"project_id":1,"user_name":1,"project_name":1,"role":1,"initials":1})))
    def projects(project):
        data={"current_user_role":role,"current_user_name":username}
        agent_list=[]
        supervisor_list = []
        agentid_list=["1","2","3","4"]
       
        for i in project:
            if i["role"]=="supervisor":
                data["supervisor"]=i["user_name"]
                supervisor_list.append(i["initials"])
            if i["role"]=="agent":
                agent_list.append(i["initials"])
            data["project_id"]=i["project_id"]
            data["project_name"]=i["project_name"]
            data["agent"] = agent_list
            data["supervisorlist"] = supervisor_list
            data["agentid"] = agentid_list
            data["number_of_agents"]=len(data["agent"])
        return data
    final_data=[]
    for i in project_list:
        final_data.append(projects(i))
    
    # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        final_data=list(filter(lambda final_data: final_data["supervisor"] ==session["user_name"], final_data))
    #   return json.dumps(final_data)
    return render_template("index.html", data=final_data)
    #   print("\n\n")
    
#get the list of onboarded agents
@app.route("/OnboardedAgent.html",methods = ['GET'])
def onboarded_agents():
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired.Please login again.")

    all_details = list(db["my_master"].find({},{"_id": 0, "user_id": 1, "user_name": 1, "onboarding_date": 1,
                                             "expiration_date": 1, "facial_img": 1, "status": 1}))    
    for i in all_details:
        for key in i.keys():
            if key == "onboarding_date":
                i[key]=str(i[key].date())
            if key == "expiration_date":
                i[key] = str(i[key].date())
            if key == "facial_img":
                i["facial_img"] = (base64.b64encode(i[key])).decode('utf-8')
    
    # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        data=[]
        for i in all_details:
            if i["user_name"] in session["agent_names"]:
                data.append(i)
        all_details=data
    return render_template("OnboardedAgent.html", ondata=all_details)
    # return render_template("onboarded_agents.html", onbdata=json.dumps(all_details))

@app.route("/OnboardedAgent/<PageNo>",methods = ['GET'])
def OnboardedAgent(PageNo):
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired.Please login again.")
    limit=10
    if(PageNo == "1"):
        offset=((int(PageNo)) * limit) - limit
    else:
         offset=((int(PageNo)) * limit) - limit
         offset=offset -1 

    all_details = list(db["my_master"].find({},{"_id": 0, "user_id": 1, "user_name": 1, "onboarding_date": 1,
                                             "expiration_date": 1, "facial_img": 1, "status": 1}).skip(offset).limit(limit)) 
    all_details2 = list(db["my_master"].find({},{"_id": 0, "user_id": 1, "user_name": 1, "onboarding_date": 1,
                                             "expiration_date": 1, "facial_img": 1, "status": 1}))                                         
    for i in all_details:
        for key in i.keys():
            if key == "onboarding_date":
                i[key]=str(i[key].date())
            if key == "expiration_date":
                i[key] = str(i[key].date())
            if key == "facial_img":
                i["facial_img"] = (base64.b64encode(i[key])).decode('utf-8')
    
    # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        data=[]
        for i in all_details:
            if i["user_name"] in session["agent_names"]:
                data.append(i)
        all_details=data
    if(all_details2 and all_details):
          total={"total_rows":len(all_details2),"data":all_details} 
          return json.dumps(total,indent=2)
    else:
         return json.dumps([],indent=2)

#get the list of onboarded agents based on statuss
@app.route('/FilterOnboardedAgent',methods=["POST"])
def FilterOnboardedAgent():
    status= request.form["fstatus"]
    name= request.form["fname"]
    pageNo= request.form["pageNo"]

    limit=10
    if(pageNo == "1"):
        offset=((int(pageNo)) * limit) - limit
    else:
         offset=((int(pageNo)) * limit) - limit
         offset=offset -1 

    if  status != "" and name != "": 
        query_result=list(db["my_master"].find({"status":status,"user_name":{"$regex":name}},{"_id": 0, "user_id": 1, "user_name": 1,
        "onboarding_date": 1, "expiration_date": 1, "facial_img": 1, "status": 1}).skip(offset).limit(limit))

        query_result2=list(db["my_master"].find({"status":status,"user_name":{"$regex":name}},{"_id": 0, "user_id": 1, "user_name": 1,
        "onboarding_date": 1, "expiration_date": 1, "facial_img": 1, "status": 1}))

    elif name != "" and  status== "":
        query_result=list(db["my_master"].find({"user_name":{"$regex":name}},{"_id": 0, "user_id": 1, "user_name": 1,
        "onboarding_date": 1, "expiration_date": 1, "facial_img": 1, "status": 1}).skip(offset).limit(limit))

        query_result2=list(db["my_master"].find({"user_name":{"$regex":name}},{"_id": 0, "user_id": 1, "user_name": 1,
        "onboarding_date": 1, "expiration_date": 1, "facial_img": 1, "status": 1}))

    elif status != "" and name =="":
        query_result=list(db["my_master"].find({"status":status},{"_id": 0, "user_id": 1, "user_name": 1,
        "onboarding_date": 1, "expiration_date": 1, "facial_img": 1, "status": 1}).skip(offset).limit(limit))

        query_result2=list(db["my_master"].find({"status":status},{"_id": 0, "user_id": 1, "user_name": 1,
        "onboarding_date": 1, "expiration_date": 1, "facial_img": 1, "status": 1}))
   
    else:
        query_result=list(db["my_master"].find({},{"_id": 0, "user_id": 1, "user_name": 1,
        "onboarding_date": 1, "expiration_date": 1, "facial_img": 1, "status": 1}).skip(offset).limit(limit))

        query_result2=list(db["my_master"].find({},{"_id": 0, "user_id": 1, "user_name": 1,
        "onboarding_date": 1, "expiration_date": 1, "facial_img": 1, "status": 1}))

    # db.users.find({"name": /.*m.*/})
    for i in query_result:
        for key in i.keys():
            if key == "onboarding_date":
                i[key]=str(i[key].date())
            if key == "expiration_date":
                i[key]=str(i[key].date())
            if key == "facial_img":
                i["facial_img"] = (base64.b64encode(i[key])).decode('utf-8')
    if session['logged_in_user_role']=="supervisor":
        data=[]
        for i in query_result:
            if i["user_name"] in session["agent_names"]:
                data.append(i)
        query_result=data
    if(query_result2 and query_result):
          total={"total_rows":len(query_result2),"data":query_result} 
          return json.dumps(total,indent=2)
    else:
         return json.dumps([],indent=2)

#filter agentwise results based on project name and date
today = date.today()
seven_days_back= today - datetime.timedelta(days=30)
to=str(today)
fro=str(seven_days_back)
time_from = datetime.datetime.strptime(fro, "%Y-%m-%d").date()

@app.route("/AgentList.html")
def agentdetails_home():
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired.Please login again.")
    time_from = datetime.datetime.strptime(fro, "%Y-%m-%d").date()
    time_to=datetime.datetime.strptime(to, "%Y-%m-%d").date()
    time_from=datetime.datetime.combine(time_from,datetime.datetime.min.time())
    time_to=datetime.datetime.combine(time_to,datetime.datetime.min.time())
    
    db = cluster["TestDb_Dilip"]
    #time_from = datetime.datetime(2022,2,20)
    #time_to=datetime.datetime(2022,2,8)
    project_names = list(db["Check1"].distinct("project"))
    #if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        data=list(db.Check1.aggregate(
                [{"$match": {
                        "project":session["user_project"].lower()
                        # "date": {"$gte":time_from,"$lte":time_to}
                }
                },
                {
                "$group": {"_id": {"name":"$name","project": "$project"},
                        "total_hours": {"$sum": "$total_hours"},"billable_hours":{"$sum":"$billable_hours"},
                        "breaks":{"$sum":"$breaks"},"non_billable_hours":{"$sum":"$non_billable hours"},
                        "COUNT": {"$sum": 1}}}]))
        db1=cluster["ProctoringAPI_DB"]
        flag_data=list(db1.my_collection.aggregate(
            [{"$match":{ "role":"agent"}},
            {"$group": {"_id": {"name":"$user_name","flags": "$flags"}}}]))
        for i in data:
            i["flags"]=0
            for j in flag_data:
                if i["_id"]["name"]==j["_id"]["name"]:
                    i["flags"]=j["_id"]["flags"]  
    else:
        data=list(db.Check1.aggregate(
                [{
                "$group": {
                        "_id": {"name":"$name","project": "$project"},
                        "total_hours": {"$sum": "$total_hours"},
                        "billable_hours":{"$sum":"$billable_hours"},
                        "breaks":{"$sum":"$breaks"},
                        "non_billable_hours":{"$sum":"$non_billable hours"},
                        "COUNT": {"$sum": 1 }}}]))
        db=cluster["ProctoringAPI_DB"]
        flag_data=list(db.my_collection.aggregate(
            [{"$match":{ "role":"agent"}},
            {"$group": {"_id": {"name":"$user_name","flags": "$flags"}}}]))
        for i in data:
            i["flags"]=0
            for j in flag_data:
                if i["_id"]["name"]==j["_id"]["name"]:
                    i["flags"]=j["_id"]["flags"]  
    for i in data:
        i["_id"]["chart_name"]=i["_id"]["name"].replace(" ","") 
   
    
    # return json.dumps(data)
    return render_template("AgentList.html", data=data)
@app.route("/AgentListData/<PageNo>",methods=["GET"])
def AgentListData(PageNo):
    limit=3
    offset=0
    if(PageNo == "1"):
        #offset=((int(PageNo)) * limit) - limit
        pass
    else:
        #offset=((int(PageNo)) * limit) - limit
        limit=3*int(PageNo)
        offset=limit-3
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired.Please login again.")
    time_from = datetime.datetime.strptime(fro, "%Y-%m-%d").date()
    time_to=datetime.datetime.strptime(to, "%Y-%m-%d").date()
    time_from=datetime.datetime.combine(time_from,datetime.datetime.min.time())
    time_to=datetime.datetime.combine(time_to,datetime.datetime.min.time())
    
    db = cluster["TestDb_Dilip"]
    if session['logged_in_user_role']=="supervisor":
        data=list(db.Check1.aggregate(
                [{"$match": {"project":session["user_project"].lower()
                        # "date": {"$gte":time_from,"$lte":time_to}
}},
                {"$group": {"_id": {"name":"$name","project": "$project"},
                    "total_hours": {"$sum": "$total_hours"},"billable_hours":{"$sum":"$billable_hours"},
                    "breaks":{"$sum":"$breaks"},"non_billable_hours":{"$sum":"$non_billable hours"},
                    "COUNT": {"$sum": 1}}},
                    {"$sort":{"_id" :-1}}
                    ]))
        db1=cluster["ProctoringAPI_DB"]
        flag_data=list(db1.my_collection.aggregate(
            [{"$match":{ "role":"agent"}},
            {"$group": {"_id": {"name":"$user_name","flags": "$flags"}}}]))
     
        for i in data:
            i["flags"]=0
            for j in flag_data:
                if i["_id"]["name"]==j["_id"]["name"]:
                    i["flags"]=j["_id"]["flags"] 
        data=data[offset:limit] 
        #print(data,sep="\n")  
    else:
        data=list(db.Check1.aggregate(
                [{
                "$group": {
                        "_id": {"name":"$name","project": "$project"},
                        "total_hours": {"$sum": "$total_hours"},
                        "billable_hours":{"$sum":"$billable_hours"},
                        "breaks":{"$sum":"$breaks"},
                        "non_billable_hours":{"$sum":"$non_billable hours"},
                        "COUNT": {"$sum": 1 }}},
                        {"$sort":{"_id" :-1}}]))
        
        db=cluster["ProctoringAPI_DB"]
        flag_data=list(db.my_collection.aggregate(
            [{"$match":{ "role":"agent"}},
            {"$group": {"_id": {"name":"$user_name","flags": "$flags"}}}]))
        #flag_data=flag_data[offset:offset+limit]
        for i in data:
            i["flags"]=0
            for j in flag_data:
                if i["_id"]["name"]==j["_id"]["name"]:
                    i["flags"]=j["_id"]["flags"]
        data=data[offset:limit] 
        #print(data,sep="\n")  
    for i in data:
        i["_id"]["chart_name"]=i["_id"]["name"].replace(" ","") 
  
    return json.dumps(data)
@app.route("/GetName")
def GetName():
    db = cluster["TestDb_Dilip"]
    #if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        data=list(db.Check1.aggregate(
                [{
            "$match": {
                    "project":session["user_project"].lower()
                    # "date": {"$gte":time_from,"$lte":time_to}
            }
            },
                {
                "$group": {
                        "_id": {
                        "name":"$name",
                        "project": "$project"
                        },
                        "total_hours": {
                        "$sum": "$total_hours"
                        },
                        "billable_hours":{
                        "$sum":"$billable_hours"
                        },
                        "breaks":{
                        "$sum":"$breaks"
                        },
                        "non_billable_hours":{
                        "$sum":"$non_billable hours"
                        },
                        "COUNT": {
                        "$sum": 1
                        }
                }
                }]
        )),
    else:
        data=list(db.Check1.aggregate(
                [
                {
                "$group": {
                        "_id": {
                        "name":"$name",
                        "project": "$project"
                        },
                        "total_hours": {
                        "$sum": "$total_hours"
                        },
                        "billable_hours":{
                        "$sum":"$billable_hours"
                        },
                        "breaks":{
                        "$sum":"$breaks"
                        },
                        "non_billable_hours":{
                        "$sum":"$non_billable hours"
                        },
                        "COUNT": {
                        "$sum": 1
                        }
                }
                }]
        )),
    for j in data:
        for i in j:
            i["_id"]["chart_name"]=i["_id"]["name"].replace(" ","")
    return json.dumps(data[0])
@app.route("/GetNameBYProject$project=<string:project>")
def GetNameBYProject(project):
    time_from = datetime.datetime.strptime(fro, "%Y-%m-%d").date()
    time_to=datetime.datetime.strptime(to, "%Y-%m-%d").date()
    time_from=datetime.datetime.combine(time_from,datetime.datetime.min.time())
    time_to=datetime.datetime.combine(time_to,datetime.datetime.min.time())
    db = cluster["TestDb_Dilip"]
    #time_from = datetime.datetime(2022,2,20)
    #time_to=datetime.datetime(2022,2,8)
    data=list(db.Check1.aggregate(
            [{
            "$match": {
                    "project":project.lower()
                    # "date": {"$gte":time_from,"$lte":time_to}
            }
            }, {
            "$group": {
                    "_id": {"name":"$name","project": "$project"},
                    "total_hours": {
                    "$sum": "$total_hours"},
                    "billable_hours":{"$sum":"$billable_hours"},
                    "breaks":{"$sum":"$breaks"
                    },
                    "non_billable_hours":{"$sum":"$non_billable hours"},
                    "COUNT": {"$sum": 1}}
            }]
    )),
    for j in data:
        for i in j:
            i["_id"]["chart_name"]=i["_id"]["name"].replace(" ","")
            
    return json.dumps(data[0],indent=2)
    #render_template("agents_list.html", data=json.dumps(data))
    #return render_template("ProjectAgentList.html", data=data)
   
#agentdetails/P001/
@app.route("/ProjectAgentList.html$project=<string:project>",methods=["GET"])
def projectagentdetails(project):
    # if not session.get("logged_in_user_role"):
    #     return render_template("login.html",data="Session expired.Please login again.")
    time_from = datetime.datetime.strptime(fro, "%Y-%m-%d").date()
    time_to=datetime.datetime.strptime(to, "%Y-%m-%d").date()
    time_from=datetime.datetime.combine(time_from,datetime.datetime.min.time())
    time_to=datetime.datetime.combine(time_to,datetime.datetime.min.time())
    db = cluster["TestDb_Dilip"]
    #time_from = datetime.datetime(2022,2,20)
    #time_to=datetime.datetime(2022,2,8)
    if not project:
        project=session["user_project"]
    #if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        data=list(db.Check1.aggregate(
                [{"$match": {
                        "project":project
                        # "date": {"$gte":time_from,"$lte":time_to}
                }
                },
                {
                "$group": {"_id": {"name":"$name","project": "$project"},
                        "total_hours": {"$sum": "$total_hours"},"billable_hours":{"$sum":"$billable_hours"},
                        "breaks":{"$sum":"$breaks"},"non_billable_hours":{"$sum":"$non_billable hours"},
                        "COUNT": {"$sum": 1}}}]))
        db1=cluster["ProctoringAPI_DB"]
        flag_data=list(db1.my_collection.aggregate(
            [{"$match":{ "role":"agent"}},
            {"$group": {"_id": {"name":"$user_name","flags": "$flags"}}}]))
        for i in data:
            i["flags"]=0
            for j in flag_data:
                if i["_id"]["name"]==j["_id"]["name"]:
                    i["flags"]=j["_id"]["flags"]  
    else:
        data=list(db.Check1.aggregate(
               [{"$match": {
                        "project":project
                        # "date": {"$gte":time_from,"$lte":time_to}
                }
                },
                {
                "$group": {
                        "_id": {"name":"$name","project": "$project"},
                        "total_hours": {"$sum": "$total_hours"},
                        "billable_hours":{"$sum":"$billable_hours"},
                        "breaks":{"$sum":"$breaks"},
                        "non_billable_hours":{"$sum":"$non_billable hours"},
                        "COUNT": {"$sum": 1 }}}]))
        db=cluster["ProctoringAPI_DB"]
        flag_data=list(db.my_collection.aggregate(
            [{"$match":{ "role":"agent"}},
            {"$group": {"_id": {"name":"$user_name","flags": "$flags"}}}]))
        for i in data:
            i["flags"]=0
            for j in flag_data:
                if i["_id"]["name"]==j["_id"]["name"]:
                    i["flags"]=j["_id"]["flags"]  
    for i in data:
        i["_id"]["chart_name"]=i["_id"]["name"].replace(" ","") 
    """ for j in data:
        for i in j:
            i["_id"]["chart_name"]=i["_id"]["user_name"].replace(" ","")"""
    # return json.dumps(data[0],indent=2)
    # render_template("agents_list.html", data=json.dumps(data))
    return render_template("ProjectAgentList.html", data=data)

#agent view along with filters 
@app.route("/FiltersAgentList",methods=["POST"])
def FiltersAgentList():
    Project= request.form["Project"]
    #print(Project)
    if not Project:
        Project=session["user_project"]
    fro= request.form["fro"]
    to= request.form["to"]
    todays_date = datetime.datetime.now()
    time_from = datetime.datetime.strptime(fro, "%Y-%m-%d").date()
    time_to=datetime.datetime.strptime(to, "%Y-%m-%d").date()
    time_from=datetime.datetime.combine(time_from,datetime.datetime.min.time())
    time_to=datetime.datetime.combine(time_to,datetime.datetime.min.time())
    db = cluster["TestDb_Dilip"]
    #time_from = datetime.datetime(2022,2,20)
    #time_to=datetime.datetime(2022,2,8)pyth
    #if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        data=list(db.Check1.aggregate(
                [{"$match": {
                         "project":Project,
                          "date": {"$gte":time_from,"$lte":time_to}
                }
                },
                {
                "$group": {"_id": {"name":"$name","project": "$project"},
                        "total_hours": {"$sum": "$total_hours"},"billable_hours":{"$sum":"$billable_hours"},
                        "breaks":{"$sum":"$breaks"},"non_billable_hours":{"$sum":"$non_billable hours"},
                        "COUNT": {"$sum": 1}}}]))
        db1=cluster["ProctoringAPI_DB"]
        flag_data=list(db1.my_collection.aggregate(
            [{"$match":{ "role":"agent"}},
            {"$group": {"_id": {"name":"$user_name","flags": "$flags"}}}]))
        for i in data:
            i["flags"]=0
            for j in flag_data:
                if i["_id"]["name"]==j["_id"]["name"]:
                    i["flags"]=j["_id"]["flags"]  
    else:
        data=list(db.Check1.aggregate(
               [{"$match": {
                         "project":Project,
                          "date": {"$gte":time_from,"$lte":time_to}
                }
                },
                {
                "$group": {
                        "_id": {"name":"$name","project": "$project"},
                        "total_hours": {"$sum": "$total_hours"},
                        "billable_hours":{"$sum":"$billable_hours"},
                        "breaks":{"$sum":"$breaks"},
                        "non_billable_hours":{"$sum":"$non_billable hours"},
                        "COUNT": {"$sum": 1 }}}]))
        db=cluster["ProctoringAPI_DB"]
        flag_data=list(db.my_collection.aggregate(
            [{"$match":{ "role":"agent"}},
            {"$group": {"_id": {"name":"$user_name","flags": "$flags"}}}]))
        for i in data:
            i["flags"]=0
            for j in flag_data:
                if i["_id"]["name"]==j["_id"]["name"]:
                    i["flags"]=j["_id"]["flags"]  
    for i in data:
        i["_id"]["chart_name"]=i["_id"]["name"].replace(" ","") 
    """ for j in data:
        for i in j:
            i["_id"]["chart_name"]=i["_id"]["user_name"].replace(" ","")"""
    return json.dumps(data)
    #render_template("agents_list.html", data=json.dumps(data))
    #render_template("AgentList.html", data=data[0])

#display all the violation details.
@app.route('/ViolationMgmt.html',methods=["GET"])
def violation_details():
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired.Please login again.")

    db=cluster.Proctoring_DB
    query_result = list(db.violation.find({"marked_as":"TBM"}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,"created_date":1,
                       "project_name":1 ,"reviewed_by": 1, "violation_image": 1}))
    
    

    for i in query_result:
        i["_id"] = str(i["_id"])
        i["created_date"]=str(i["created_date"].date())
        i["violation_image"] = (base64.b64encode(i["violation_image"])).decode('utf-8')
    # return json.dumps(query_result,indent=2)
    # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        data=[]
        for i in query_result:
            if i["user_name"] in session["agent_names"]:
                data.append(i)
        query_result=data
    return render_template("ViolationMgmt.html", data=query_result)

@app.route('/ViolationMgmt/<PageNo>',methods=["GET"])
def ViolationMgmt(PageNo):
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired.Please login again.")
    limit=10
    if(PageNo == "1"):
        offset=((int(PageNo)) * limit) - limit

    else:
         offset=((int(PageNo)) * limit) - limit
         offset=offset -1 

    db=cluster.Proctoring_DB
    query_result = list(db.violation.find({"marked_as":"TBM"}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,"created_date":1,
                       "project_name":1 ,"reviewed_by": 1, "violation_image": 1}).skip(offset).limit(limit))
    query_result2 = list(db.violation.find({"marked_as":"TBM"}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,"created_date":1,
                       "project_name":1 ,"reviewed_by": 1, "violation_image": 1}))
    
    for i in query_result:
        i["_id"] = str(i["_id"])
        i["created_date"]=str(i["created_date"].date())
        i["violation_image"] = (base64.b64encode(i["violation_image"])).decode('utf-8')
    # return json.dumps(query_result,indent=2)
    # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        data=[]
        for i in query_result:
            if i["user_name"] in session["agent_names"]:
                data.append(i)
        query_result=data
    if(query_result and query_result2):
      total={"total_rows":len(query_result2),"data":query_result} 
      return json.dumps(total,indent=2)
    else:
      return json.dumps([],indent=2)

#display  details based on project name and from and to date
@app.route('/ViolationMgmt.html/<string:project>',defaults={"fro":fro,"to":to},methods=["GET"])
@app.route("/ViolationMgmt.html/<string:project>/<string:fro>/<string:to>")
def violation_details_filter(project,fro,to):
    time_from = datetime.datetime.strptime(fro, "%Y-%m-%d").date()
    time_to=datetime.datetime.strptime(to, "%Y-%m-%d").date()
    time_from=datetime.datetime.combine(time_from,datetime.datetime.min.time())
    time_to=datetime.datetime.combine(time_to,datetime.datetime.min.time())
    #print(time_from,time_to,sep="\n")
    #time_from = datetime.datetime(2022,2,20)
    #time_to=datetime.datetime(2022,2,8)
    data=list(db.violation.find({"project_name":project,"date": {"$gte":time_from,"$lte":time_to}}))
    for i in data:
            i["_id"]= str(i["_id"])
            i["date"]=str(i["date"].date())
            i["violation_image"]=(base64.b64encode(i["violation_image"])).decode('utf-8')
    # return json.dumps(data,indent=2)
    #if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        x=[]
        for i in data:
            if i["user_name"] in session["agent_names"]:
                x.append(i)
        data=x
    return render_template("ViolationMgmt.html", data=data)


@app.route('/escalated_agents/<PageNo>',methods=["GET"])
def escalated_agents(PageNo):
    # if not session.get("logged_in_user_role"):
    #     data={"current_user_role":session.get("logged_in_user_role")}
        # return json.dumps(data)   
    limit=10
    if(PageNo == "1"):
        offset=((int(PageNo)) * limit) - limit

    else:
         offset=((int(PageNo)) * limit) - limit
         offset=offset -1 
    
    db=cluster.Proctoring_DB
    dbResponse = list(db.violation.find({"marked_as":"ES"}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "escalated_by": 1 ,"violation_image":1,"project_name":1,"created_date":1}).skip(offset).limit(limit))
    dbResponse0 = list(db.violation.find({"marked_as":"ES"}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "escalated_by": 1 ,"violation_image":1,"project_name":1,"created_date":1}))
  # return Response(response=json.dumps({"message": "marked_as field updated successfully"}))
        # return render_template("ViolationMgmt.html", data=dbResponse)
        # return render_template("ViolationMgmt.html",data = dbResponse)
    for i in dbResponse:
          i["_id"] = str(i["_id"]) 
          i["created_date"]=str(i["created_date"])
          i["violation_image"] = (base64.b64encode(i["violation_image"])).decode('utf-8')

              
        # print(dbResponse)
        # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
         data=[]
         for i in dbResponse:
                if i["user_name"] in session["agent_names"]:
                    data.append(i)
         dbResponse=data  
    if(dbResponse and dbResponse0):
      total={"total_rows":len(dbResponse0),"data":dbResponse} 
      return json.dumps(total,indent=2)
    else:
      return json.dumps([],indent=2)

# to update individual violations of a particulat violation image that takes in documnet ID as input
@app.route('/ViolationMgmt/<id>/<marked_as>/<username>',methods=["GET"])
def update_markedas(id,marked_as,username):
    #  if not session.get("logged_in_user_role"):
    #     return render_template("login.html",data="Session expired.Please login again.")
     db=cluster.Proctoring_DB
     dbResponse = db.violation.update_one({"_id": ObjectId(id)},
                                                    {"$set": {"marked_as":marked_as}})
     db=cluster["Proctoring_DB"]
     x=list(db.violation.aggregate(
                    [{"$match":{ "user_name":username,
                    "marked_as":"ES"}},
                    {"$group": {"_id": {"user_name":"$user_name","project_name": "$project_name"},
                    "COUNT": {"$sum": 1}}}]))
     count=x[0]["COUNT"]
     db = cluster["ProctoringAPI_DB"]
     db.my_collection.update_one({"user_name":username},{"$set": {"flags":count}})
     return Response(response=json.dumps({"message": "marked_as field updated successfully"}))

       
# to display list of projects to the super admin
@app.route("/Configurations.html",methods = ["GET"])
def configuration():
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired")
    project_names = list(db["my_collection"].distinct("project_name"))
    # return json.dumps(project_names,indent=2)
    return render_template("Configurations.html",data = project_names)


@app.route("/violation_update",methods = ["POST","GET"])
def violation_update():
    mobile=request.form["mobile"]
    book=request.form["book"]
    multiple=request.form["multiple"]
    no_person=request.form["no_person"]
    
    #print(mobile,book,multiple,no_person,sep="\n")
    project_names = list(db["my_collection"].distinct("project_name"))
    dbResponse = db.my_collection.update_many({"project_name":request.form["projectName"]},
                                            {"$set": {"violation_filter.mobile":mobile,\
                                                "violation_filter.multiple_persons":multiple,\
                                                    "violation_filter.book":book,
                                                    "violation_filter.no_person":no_person}})
    return Response(response=json.dumps({"message": "violation_filter field updated successfully"}))
    #return redirect(url_for("Configurations.html"))

@app.route("/GetViolation",methods = ["GET"])
def GetViolation():
    db=cluster["Proctoring_DB"]
    data = list(db.violation.distinct("violation_type"))
    return json.dumps(data,indent=2)


@app.route("/GetProjectByConfigurations$project=<string:project_name>",methods = ["GET"])   
def configurations_list(project_name):

    data=list(db.my_collection.find({"project_name":project_name},{"violation_filter":1,"_id":0}))

    return json.dumps(data[0])

#to display list of agents
@app.route('/UserManagement.html',methods=["GET"])
def userManagement():
    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired")
    db1=cluster["Proctoring_DB"]
    today = datetime.datetime.combine(date.today(), datetime.datetime.min.time())
    data=list(db1.dailySession.find({"session_date_string":str(today)},{"_id":0,"user_id":1,"user_name":1,"project_name":1,"login_time":1,"logout_time":1,"session_status":1}))
    # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        x=[]
        for i in data:
            if i["user_name"] in session["agent_names"]:
                x.append(i)
        data=x
    return render_template('UserManagement.html', data=data)

@app.route('/UserManagement/<PageNo>',methods=["GET"])
def userManagementData(PageNo):
    limit=10
    if(PageNo == "1"):
        offset=((int(PageNo)) * limit) - limit
    else:
        offset=((int(PageNo)) * limit) - limit
        offset=offset -1

    if not session.get("logged_in_user_role"):
        return render_template("login.html",data="Session expired")
    db1=cluster["Proctoring_DB"]
    today = datetime.datetime.combine(date.today(), datetime.datetime.min.time())
    data=list(db1.dailySession.find({"session_date_string":str(today)},{"_id":0,"user_id":1,"user_name":1,"project_name":1,"login_time":1,"logout_time":1,"session_status":1}).skip(offset).limit(limit))
    data1=list(db1.dailySession.find({"session_date_string":str(today)},{"_id":0,"user_id":1,"user_name":1,"project_name":1,"login_time":1,"logout_time":1,"session_status":1}))
    
    for i in data:
        for key in i.keys():
            if key == "login_time":
                i[key] = str(i[key])
            if key == "logout_time":
                i[key] = str(i[key])
    # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        x=[]
        for i in data:
            if i["user_name"] in session["agent_names"]:
                x.append(i)
        data=x
    if(data and data1):
        total={"total_rows":len(data1),"data":data} 
        return json.dumps(total,indent=2)
    else:
        return json.dumps([],indent=2)

@app.route('/FilterbyAgents',methods=["POST"])
def FilterbyAgents():
    db1=cluster["Proctoring_DB"]
    pageNo= request.form["pageNo"]
    name= request.form["fname"]
    project=""
    if session['logged_in_user_role']!="super admin":
           project= request.form["fProject"]

    limit=10
    if(pageNo == "1"):
        offset=((int(pageNo)) * limit) - limit
    else:
         offset=((int(pageNo)) * limit) - limit
         offset=offset -1 
    today = datetime.datetime.combine(date.today(), datetime.datetime.min.time())
    if  project != "" and name != "": 
        data=list(db1.dailySession.find({"session_date_string":str(today),"project_name":project,"user_name":{"$regex":name}},{"_id": 0,"user_id": 1, "user_name": 1,"project_name":1,"login_time":1,"logout_time":1,"session_status": 1}).skip(offset).limit(limit))
        data2=list(db1.dailySession.find({"session_date_string":str(today),"project_name":project,"user_name":{"$regex":name}},{"_id": 0,"user_id": 1, "user_name": 1,"project_name":1,"login_time":1,"logout_time":1,"session_status": 1}))
    elif name != "" and  project== "":
        data=list(db1.dailySession.find({"session_date_string":str(today),"user_name":{"$regex":name}},{"_id": 0, "user_id": 1, "user_name": 1,"project_name":1,"login_time":1,"logout_time":1,"session_status": 1}).skip(offset).limit(limit))
        data2=list(db1.dailySession.find({"session_date_string":str(today),"user_name":{"$regex":name}},{"_id": 0, "user_id": 1, "user_name": 1,"project_name":1,"login_time":1,"logout_time":1,"session_status": 1}))

    elif project != "" and name =="":
        data=list(db1.dailySession.find({"session_date_string":str(today),"project_name":project},{"_id": 0, "user_id": 1, "user_name": 1,"project_name":1,"login_time":1,"logout_time":1, "session_status": 1}).skip(offset).limit(limit))
        data2=list(db1.dailySession.find({"session_date_string":str(today),"project_name":project},{"_id": 0, "user_id": 1, "user_name": 1,"project_name":1,"login_time":1,"logout_time":1, "session_status": 1})) 
    else:
        data=list(db1.dailySession.find({"session_date_string":str(today)},{"_id": 0, "user_id": 1, "user_name": 1,"project_name":1,"login_time":1,"logout_time":1,"session_status": 1}).skip(offset).limit(limit))
        data2=list(db1.dailySession.find({"session_date_string":str(today)},{"_id": 0, "user_id": 1, "user_name": 1,"project_name":1,"login_time":1,"logout_time":1,"session_status": 1}))

    for i in data:
        for key in i.keys():
            if key == "login_time":
                i[key] = str(i[key])
            if key == "logout_time":
                i[key] = str(i[key])
            
    if session['logged_in_user_role']=="supervisor":
        x=[]
        for i in data:
            if i["user_name"] in session["agent_names"]:
                x.append(i)
        data=x
    if(data and data2):
      total={"total_rows":len(data2),"data":data} 
      return json.dumps(total,indent=2)
    else:
      return json.dumps([],indent=2)

#to display live (online) agents
@app.route('/user_live/<PageNo>')
# @app.route('/')
def user_live(PageNo):
    db = cluster.Proctoring_DB
    today = datetime.datetime.combine(date.today(), datetime.datetime.min.time())
    limit=10
    if(PageNo == "1"):
        offset=((int(PageNo)) * limit) - limit
    else:
         offset=((int(PageNo)) * limit) - limit
         offset=offset -1

    data = list(db.dailySession.find({"session_date_string": str(today), "session_status": "live"},
                                     {"_id": 0, "session_date_string": 0, 'billable_hours': 0, 'total_hours': 0,
                                      'non_billable_hours': 0, }).skip(offset).limit(limit))
    data1 = list(db.dailySession.find({"session_date_string": str(today), "session_status": "live"},
                                     {"_id": 0, "session_date_string": 0, 'billable_hours': 0, 'total_hours': 0,
                                      'non_billable_hours': 0, }))
    for i in data:
        for key in i.keys():
            if key == "login_time":
                i[key] = str(i[key])
            if key == "logout_time":
                i[key] = str(i[key])
            if key == 'session_date':
                i[key] = str(i[key])
    # if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        x=[]
        for i in data:
            if i["user_name"] in session["agent_names"]:
                x.append(i)
        data=x
    if(data and data1):
      total={"total_rows":len(data1),"data":data} 
      return json.dumps(total,indent=2)
    else:
      return json.dumps([],indent=2) 

#display list of all the agents
@app.route('/users_list')
def user_list():
    
    
    # db=cluster.ProctoringAPI_DB
    # data=list(db.my_collection.find({"role":"agent"},{"_id":0,"user_id":1,"user_name":1,"project_id":1,"project_name":1,"status":1}))
    db1=cluster["Proctoring_DB"]
    today = datetime.datetime.combine(date.today(), datetime.datetime.min.time())
    data=list(db1.dailySession.find({"session_date_string":str(today)},{"_id":0,"user_id":1,"user_name":1,"project_name":1,"login_time":1,"logout_time":1,"session_status":1}))
    #if user_role=="supervisor":
    if session['logged_in_user_role']=="supervisor":
        x=[]
        for i in data:
            if i["user_name"] in session["agent_names"]:
                x.append(i)
        data=x
    return json.dumps(data,indent=2)
    # return render_template('UserManagement.html', data=data)
@app.route("/GetProjectName",methods = ["GET"])
def GetProjectName():
        project_names = list(db["my_collection"].distinct("project_name"))
        return json.dumps(project_names,indent=2)


@app.route('/FilterbyViolation',methods=["POST"])
def FilterbyViolation():
    db1=cluster["Proctoring_DB"]
    violation= request.form["violation"]
    name= request.form["name"]
    pageNo= request.form["pageNo"]
    limit=10
    if(pageNo == "1"):
        offset=((int(pageNo)) * limit) - limit
    else:
         offset=((int(pageNo)) * limit) - limit
         offset=offset -1 
  
    if  violation != "" and name != "": 
        query_result = list(db1.violation.find({"marked_as":"TBM","user_name":{"$regex":name},"violation_type":violation},{"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "reviewed_by": 1, "violation_image": 1,"project_name":1,"created_date":1}).skip(offset).limit(limit))
        query_result2 = list(db1.violation.find({"marked_as":"TBM","user_name":{"$regex":name},"violation_type":violation},{"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "reviewed_by": 1, "violation_image": 1,"project_name":1,"created_date":1}))
    elif name != "" and  violation== "":
        query_result = list(db1.violation.find({"marked_as":"TBM","user_name":{"$regex":name}}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "reviewed_by": 1, "violation_image": 1,"project_name":1,"created_date":1}).skip(offset).limit(limit))
        query_result2 = list(db1.violation.find({"marked_as":"TBM","user_name":{"$regex":name}}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "reviewed_by": 1, "violation_image": 1,"project_name":1,"created_date":1}))
    elif violation != "" and name =="":
       query_result = list(db1.violation.find({"marked_as":"TBM","violation_type":violation}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "reviewed_by": 1, "violation_image": 1,"project_name":1,"created_date":1}).skip(offset).limit(limit))
       query_result2 = list(db1.violation.find({"marked_as":"TBM","violation_type":violation}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "reviewed_by": 1, "violation_image": 1,"project_name":1,"created_date":1}))
    else:
        query_result = list(db1.violation.find({"marked_as":"TBM"}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "reviewed_by": 1, "violation_image": 1,"project_name":1,"created_date":1}).skip(offset).limit(limit))
        query_result2 = list(db1.violation.find({"marked_as":"TBM"}, {"_id": 1, "violation_type": 1,"user_id":1, "user_name": 1, "marked_as": 1,
                                                  "reviewed_by": 1, "violation_image": 1,"project_name":1,"created_date":1}))
    for i in query_result:
        i["_id"] = str(i["_id"])
        i["created_date"]=str(i["created_date"].date())
        i["violation_image"] = (base64.b64encode(i["violation_image"])).decode('utf-8')
    if(query_result2 and query_result):
          total={"total_rows":len(query_result2),"data":query_result} 
          return json.dumps(total,indent=2)
    else:
         return json.dumps([],indent=2)
    
@app.route("/LogOut",methods = ["GET"])
def LogOut():
    session.pop('logged_in_user_role', None)
    session.pop('logged_in_user_id', None)       
    return render_template("login.html")

@app.route("/Error")
def Error():
    return render_template("Error.html")
    
if __name__ == "__main__":
    app.run(host="localhost", debug=True)#port=443,)
    #app.run(host="0.0.0.0", port=443,debug=False)