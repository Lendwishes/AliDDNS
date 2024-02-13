from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
 
# 加载获取 、 新增、 更新、 删除接口
from aliyunsdkalidns.request.v20150109 import DescribeSubDomainRecordsRequest, AddDomainRecordRequest, UpdateDomainRecordRequest, DeleteDomainRecordRequest
 
# 加载内置模块
import json,urllib,os,socket,requests,time
 
# 获取ID以及SECRET
ConfigFile = open("config.ini","r",encoding="UTF-8")
ConfigContent  = ConfigFile.read().split("\n")
ID = ConfigContent[1]
SECRET = ConfigContent[3]
regionId = ConfigContent[15]
client = AcsClient(ID, SECRET, regionId)
DomainName = ConfigContent[5]
SubDomainList = ConfigContent[7].split(";")
DNSTypeList = ConfigContent[9].split(";")
PrivateSatList = ConfigContent[11].split(";")
TTL = ConfigContent[13]
DoRepeat = int(ConfigContent[17])

# 获取外网IP  三个地址返回的ip地址格式各不相同，3322 的是最纯净的格式， 备选1为 json格式 备选2 为curl方式获取 两个备选地址都需要对获取值作进一步处理才能使用
def getIp(rr):
  DNSType = DNSTypeList[SubDomainList.index(rr)]
  PrivateSat = int(PrivateSatList[SubDomainList.index(rr)])
  if PrivateSat:
    ip = socket.gethostbyname(socket.gethostname())
  else:
    if DNSType == "A":
      with urllib.request.urlopen('http://www.3322.org/dyndns/getip') as response:
        html = response.read()
        ip = str(html, encoding='utf-8').replace("\n", "")
    elif DNSType == "AAAA":
      ip = requests.get('https://v6.ident.me').text
  return ip
 
# 查询记录
def getDomainInfo(SubDomain):
  request = DescribeSubDomainRecordsRequest.DescribeSubDomainRecordsRequest()
  request.set_accept_format('json')
 
  # 设置要查询的记录类型为 A记录  官网支持A / CNAME / MX / AAAA / TXT / NS / SRV / CAA / URL隐性（显性）转发 如果有需要可将该值配置为参数传入
  request.set_Type(DNSTypeList[SubDomainList.index(SubDomain)])
 
  # 指定查记的域名 格式为 'test.example.com'
  request.set_SubDomain(SubDomain + '.' + DomainName)
 
  response = client.do_action_with_exception(request)
  response = str(response, encoding='utf-8')
 
  # 将获取到的记录转换成json对象并返回
  return json.loads(response)
 
# 新增记录 (默认都设置为A记录，通过配置set_Type可设置为其他记录)
def addDomainRecord(client,rr,domainname):
  request = AddDomainRecordRequest.AddDomainRecordRequest()
  request.set_accept_format('json')
 
  # request.set_Priority('1') # MX 记录时的必选参数
  request.set_TTL(ConfigContent[13])
  request.set_Value(getIp(rr))   # 新增的 ip 地址
  request.set_Type(DNSTypeList[SubDomainList.index(rr)])    # 记录类型
  request.set_RR(rr)      # 子域名名称 
  request.set_DomainName(domainname) #主域名
 
  # 获取记录信息，返回信息中包含 TotalCount 字段，表示获取到的记录条数 0 表示没有记录， 其他数字为多少表示有多少条相同记录，正常有记录的值应该为1，如果值大于1则应该检查是不是重复添加了相同的记录
  response = client.do_action_with_exception(request)
  response = str(response, encoding='utf-8')
  relsult = json.loads(response)
  return relsult
 
# 更新记录
def updateDomainRecord(client,rr,record_id):
  request = UpdateDomainRecordRequest.UpdateDomainRecordRequest()
  request.set_accept_format('json')
 
  # request.set_Priority('1')
  request.set_TTL(TTL)
  request.set_Value(getIp(rr)) # 新的ip地址
  request.set_Type(DNSTypeList[SubDomainList.index(rr)])
  request.set_RR(rr)
  request.set_RecordId(record_id) # 更新记录需要指定 record_id ，该字段为记录的唯一标识，可以在获取方法的返回信息中得到该字段的值
 
  response = client.do_action_with_exception(request)
  response = str(response, encoding='utf-8')
  return response
 
# 删除记录
def delDomainRecord(client,subdomain):
  info = getDomainInfo(subdomain)
  if info['TotalCount'] == 0:
    print('没有相关的记录信息，删除失败！')
  elif info["TotalCount"] == 1:
    print('准备删除记录')
    request = DeleteDomainRecordRequest.DeleteDomainRecordRequest()
    request.set_accept_format('json')
 
    record_id = info["DomainRecords"]["Record"][0]["RecordId"]
    request.set_RecordId(record_id) # 删除记录需要指定 record_id ，该字段为记录的唯一标识，可以在获取方法的返回信息中得到该字段的值
    result = client.do_action_with_exception(request)
    print('删除成功，返回信息：')
    print(result)
  else:
    # 正常不应该有多条相同的记录，如果存在这种情况，应该手动去网站检查核实是否有操作失误
    print("存在多个相同子域名解析记录值，请核查后再操作！")
 
# 有记录则更新，没有记录则新增
def setDomainRecord(client,rr,domainname):
  info = getDomainInfo(rr)
  if info['TotalCount'] == 0:
    print('准备添加新记录')
    add_result = addDomainRecord(client,rr,domainname)
    print(add_result)
  elif info["TotalCount"] == 1:
    print('准备更新已有记录')
    record_id = info["DomainRecords"]["Record"][0]["RecordId"]
    cur_ip = getIp(rr)
    old_ip = info["DomainRecords"]["Record"][0]["Value"]
    if cur_ip == old_ip:
      print ("新ip与原ip相同，无法更新！")
    else:
      update_result = updateDomainRecord(client,rr,record_id)
      print('更新成功，返回信息：')
      print(update_result)
  else:
    # 正常不应该有多条相同的记录，如果存在这种情况，应该手动去网站检查核实是否有操作失误
    print("存在多个相同子域名解析记录值，请核查删除后再操作！")
 
def start():
  for x in SubDomainList:
    setDomainRecord(client,x,DomainName)
 
# 循环子域名列表进行批量操作
if DoRepeat == 0:
  start()
else:
  while True:
    start()
    time.sleep(DoRepeat)
