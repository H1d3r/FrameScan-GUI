import sys
import json
import queue
import os
import threading
from socket import *
from urllib.parse import urlparse
import inspect
from Modules import Public
from Modules import BaseInfo
from Modules import CyberCalculate
import eventlet
from PySide6.QtCore import QThread, Signal
from Modules.Class_Poc import Class_Poc
import yaml

class Vuln_Scanner(QThread):
    _data = Signal(dict)  # 信号类型 str  更新table

    def __init__(self,plugins_dir_name,yaml_plugins_dir_name, logger, timeout, jump_url, jump_fofa, threadnum, heads, target, poc_data,
                 plugins_temp_data, parent=None):
        super(Vuln_Scanner, self).__init__(parent)
        self.timeout = timeout
        self.vuln_portQueue = queue.Queue()
        self.plugins_dir_name = plugins_dir_name
        self.yaml_plugins_dir_name = yaml_plugins_dir_name
        self.logger = logger
        self.jump_url = jump_url
        self.jump_fofa = jump_fofa
        self.threadnum = threadnum
        self.heads = heads
        self.target = target
        self.poc_data = poc_data
        self.plugins_temp_data = plugins_temp_data

    def run(self):
        # print(self.poc_data)
        # 获取是否跳过fofa检测

        if self.jump_fofa:
            check_fofa = "1"
        else:
            check_fofa = "0"
        heads = self.heads.splitlines()
        self.heads = {}
        for head in heads:
            head = head.split(':')
            self.heads[head[0].strip()] = head[1].strip()

        if not self.target:
            self._update_log('未获取到URL地址')
            self._update_log("扫描结束")
            return
        # print(poc_data)
        if not self.poc_data:
            self._update_log("未选择插件。")
            self._update_log("扫描结束。")
            return
        else:
            self._update_log("共加载%s个插件。" % (len(self.poc_data)))
            self._update_log("共获取到%s个URL地址。" % (len(self.target)))
            self._update_log("正在创建队列...")
            self.add_queue(check_fofa)

    def get_port(self, url):
        # print(url)
        _url = urlparse(url)
        # print(_url)
        hostname = _url.hostname
        port = _url.port
        scheme = _url.scheme
        path = _url.path
        if port is None and scheme == 'https':
            port = 443
        elif port is None:
            port = 80

        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            url = scheme + '://' + hostname + path
        else:
            url = scheme + '://' + hostname + ':' + str(port) + path
        if 'http://' not in url.lower() and 'http' not in url.lower():
            url = 'http://' + hostname + ':' + str(port) + path
        return url, hostname, port, scheme

    def add_queue(self, check_fofa):
        # print(self.poc_data)
        num = 0
        if not self.jump_url:
            num = len(self.target)
            for u in self.target:
                hostname_port_scheme = self.get_port(u)
                url = hostname_port_scheme[0]
                for xuanzhong_data in self.poc_data:
                    if xuanzhong_data['vuln_file'].endswith('.yaml'):
                        filename = self.yaml_plugins_dir_name + '/' + xuanzhong_data[
                        'vuln_file']
                    else:
                        filename = self.plugins_dir_name + '/' + xuanzhong_data['cms_name'] + '/' + xuanzhong_data[
                        'vuln_file']
                    
                    # url  filename heads poc fofa_link  fofa  check_fofa
                    if not xuanzhong_data.get('FofaQuery_type'):
                        xuanzhong_data['FofaQuery_type'] = 'socket'
                    if not xuanzhong_data.get('FofaQuery_link'):
                        xuanzhong_data['FofaQuery_link'] = '/'
                    self.vuln_portQueue.put(
                        url + '$$$' + filename + '$$$' + json.dumps(self.heads) + '$$$' + xuanzhong_data[
                            'cms_name'] + "$$$" + xuanzhong_data['vuln_name'] + '$$$' + xuanzhong_data[
                            'FofaQuery_type'] + '$$$' + xuanzhong_data['FofaQuery_link'] + '$$$' + xuanzhong_data[
                            'FofaQuery_rule'] + '$$$' + check_fofa)

        elif self.jump_url:
            self._update_log("正在进行地址存活检测...")
            false_url = []
            for u in self.target:
                hostname_port_scheme = self.get_port(u)
                hostname = hostname_port_scheme[1]
                port = hostname_port_scheme[2]
                try:
                    if u not in false_url:
                        time22 = self.timeout
                        result = self.port_scanner(hostname, port, time22)
                        if result:
                            for xuanzhong_data in self.poc_data:
                                # print(poc_data)
                                if xuanzhong_data['vuln_file'].endswith('.yaml'):
                                    filename = self.plugins_dir_name + '/' + xuanzhong_data['cms_name'] + '/' + xuanzhong_data[
                                    'vuln_file']
                                else:
                                    filename = self.plugins_dir_name + '/' + xuanzhong_data['cms_name'] + '/' + \
                                           xuanzhong_data['vuln_file']
                                self.vuln_portQueue.put(
                                    u + '$$$' + filename + '$$$' + json.dumps(self.heads) + '$$$' + xuanzhong_data[
                                        'cms_name'] + "$$$" + xuanzhong_data['vuln_name'] + '$$$' + xuanzhong_data[
                                        'FofaQuery_type'] + '$$$' + xuanzhong_data[
                                        'FofaQuery_link'] + '$$$' + xuanzhong_data[
                                        'FofaQuery_rule'] + '$$$' + check_fofa)
                            num += 1
                        else:
                            false_url.append(u)
                            self._update_log("%s----无法访问。" % u)

                    else:
                        continue
                except Exception as  e:
                    self.logger.error(str(e) + '----' + str(e.__traceback__.tb_lineno) + '行')
                    false_url.append(u)
                    self._update_log("%s----无法访问。" % u)

                    continue
                    # 限制线程数小于队列大小
        self._update_log("共获取到%s个有效URL地址。" % num)
        if self.threadnum > self.vuln_portQueue.qsize():
            self.threadnum = self.vuln_portQueue.qsize()
        # print(portQueue.qsize())
        if num == 0:
            self._update_log("扫描结束。")
            return
        else:
            self._update_log("扫描开始...")
            self.thread_list = []
            for i in range(self.threadnum):
                thread = threading.Thread(target=self.vuln_scan, args=())
                thread.setDaemon(True)  # 设置为后台线程，这里默认是False，设置为True之后则主线程不用等待子线程
                self.thread_list.append(thread)

            for i in self.thread_list:
                i.start()
            for i in self.thread_list:
                i.join()
            self._update_log("扫描结束!")


    def vuln_scan(self):
        # print(portQueue.queue)  #输出所有队列

        while 1:
            try:
                if self.vuln_portQueue.empty():  # 队列空就结束
                    return
                else:
                    # url  filename heads cms_name  vuln_name fofa_type fofa_link  fofa_rule  check_fofa
                    all = self.vuln_portQueue.get().split('$$$')  # 从队列中取出 #0
                    url = all[0]
                    filename = all[1]
                    heads_dict = json.loads(all[2])
                    cms_name = all[3]
                    vuln_name = all[4]
                    fofa_type = all[5]
                    fofa_link = all[6]
                    fofa_rule = all[7]
                    check_fofa = all[8]
                    timeout = self.timeout
                    hostname_port_scheme = self.get_port(url)
                    url = hostname_port_scheme[0]
                    hostname = hostname_port_scheme[1]
                    port = hostname_port_scheme[2]
                    scheme = hostname_port_scheme[3]
                    self.logger.info("Scanner:" + url + " " + str(cms_name + "|" + vuln_name))
                    self._update_log("正在扫描【%s】" % str(cms_name + "|" + vuln_name))
                    if check_fofa == "1":
                        # print(fofa_type,fofa_link)
                        if fofa_type == 'http':
                            if fofa_rule and fofa_link != "all":
                                fofa_url = url + '/' + fofa_link
                            elif fofa_rule and fofa_link == "all":
                                fofa_url = url
                            elif not fofa_rule:
                                self._update_log("FOFA规则不存在！ %s" % filename)
                                continue
                            fofaquery = fofa_rule.lower()
                            responce = BaseInfo.http_info(fofa_url)
                            oOperand = {"data": responce}
                            oCyberCalc = CyberCalculate.CyberCalculate(szHayStack=oOperand, szRule=fofaquery,
                                                                       szSplit='=')
                            blMatch = oCyberCalc.Calculate()

                        elif fofa_type == 'socket':
                            # print(11)
                            sk = socket(AF_INET, SOCK_STREAM)
                            sk.settimeout(5)
                            try:
                                sk.connect((hostname, int(port)))
                                blMatch = True
                            except Exception:
                                blMatch = False
                            sk.close()

                        else:
                            self._update_log("未知的FofaQuery_type！ %s" % filename)
                            continue

                        # print(fofaquery[0])
                        if blMatch:
                            # 超时限制
                            try:
                                eventlet.monkey_patch(thread=False, time=True)
                                with eventlet.Timeout(timeout, False):
                                    self.scan_gogogogo(filename, url, hostname, port, scheme, heads_dict)
                                    continue
                                self._update_log("Error:%s脚本运行超时！" % filename)
                                continue
                            except Exception as e:
                                self.logger.error(str(e) + '----' + str(e.__traceback__.tb_lineno) + '行')
                                self._update_log(
                                    "Error:%s----%s----%s。" % (url, cms_name + '|' + vuln_name, '脚本运行超时'))
                                continue
                            # 进行扫描
                        else:
                            self._update_log("%s----%s----%s。" % (url, cms_name + '|' + vuln_name, 'FoFA信息不匹配'))

                    else:
                        # 超时限制
                        try:
                            eventlet.monkey_patch(thread=False, time=True)
                            with eventlet.Timeout(timeout, False):
                                try:
                                    self.scan_gogogogo(filename, url, hostname, port, scheme, heads_dict)
                                    continue
                                except Exception as  e:
                                    self.logger.error(str(e) + '----' + str(e.__traceback__.tb_lineno) + '行')
                                    self._update_log(
                                        "Error:%s脚本执行错误！<br>[Exception]:<br>%s" % (filename, e))
                                    continue
                            self._update_log("Error:%s脚本运行超时！" % (filename))
                        except Exception as e:
                            self.logger.error(str(e) + '----' + str(e.__traceback__.tb_lineno) + '行')
                            self._update_log(
                                "Error:%s----%s----%s。" % (url, cms_name + '|' + vuln_name, '脚本运行超时'))
                            continue
            except Exception as e:
                self.logger.error(str(e) + '----' + str(e.__traceback__.tb_lineno) + '行')
                self._update_log(
                    "Error:%s脚本执行错误！<br>[Exception]:<br>%s" % (filename, str(e)))
                continue
    def vuln_scan_yaml(self,poc_filename, url, hostname, port, scheme, heads_dict):
        try:
            f=open(poc_filename,"r",encoding="utf-8")
            poc = yaml.load(f,Loader=yaml.FullLoader)
            f.close()
            poc_obj  = Class_Poc(url,poc,timeout,False)
            result = poc_obj.main()
            poc_info = {
                'url': url,
                'path': poc_filename,
                'cms_name': poc.get("detail").get('category')
            }
            vuln_info={
                "vuln_name":poc.get("detail").get('name')
                }
            ret_result = {
                "Result":result.get("result"),
                "Result_Info":result.get("others"),
            }
            self.scan_result_out(ret_result, vuln_info, poc_info)
        except Exception as e:
            self.logger.error(str(e) + '----' + str(e.__traceback__.tb_lineno) + '行')
            return
    def vuln_scan_python(self,filename, url, hostname, port, scheme, heads_dict):
        nnnnnnnnnnnn1 = Public.get_obj_by_path(filename)
        if nnnnnnnnnnnn1:
            vuln_info = nnnnnnnnnnnn1.vuln_info()
            temp_cms_name = os.path.dirname(filename + ".py")  # 先获取文件路径
            cms_name = os.path.basename(temp_cms_name)

            poc_info = {
                'url': url,
                'path': filename,
                'cms_name': cms_name
            }
            Function_Out = getattr(self, 'scan_log_out')  # 以字符串的形式执行函数
            result = nnnnnnnnnnnn1.do_poc(url, hostname, port, scheme, heads_dict, Function_Out, self.plugins_temp_data)
            if not result:
                result = {"Result": False, "Result_Info": ""}
            self.scan_result_out(result, vuln_info, poc_info)
        else:
            self._update_log(filename + " 该模块未找到！")
    def scan_gogogogo(self, filename, url, hostname, port, scheme, heads_dict):
        filename = (filename).replace("\\", "//")
        if  filename.endswith(".yaml"):
            self.vuln_scan_yaml(filename, url, hostname, port, scheme, heads_dict)
        else:
            self.vuln_scan_python(filename, url, hostname, port, scheme, heads_dict)


        

    def _update_log(self, info):
        result = {"type": "log", "log_info": str(info)}
        self._data.emit(result)


    def scan_log_out(self, log_type='Debug', log_info=""):
        caller = inspect.stack()
        caller_methos = caller[1].frame
        # 获取所有请求值
        localvars = caller_methos.f_locals
        file_path = caller[1][1]
        file_path = os.path.splitext(file_path)[0]
        nnnnnnnnnnnn1 = Public.get_obj_by_path(file_path)
        if nnnnnnnnnnnn1:
            vuln_info = nnnnnnnnnnnn1.vuln_info()
            temp_cms_name = os.path.dirname(file_path + ".py")  # 先获取文件路径
            cms_name = os.path.basename(temp_cms_name)
            result = {
                "url": localvars.get('url'),
                "poc_file": file_path,
                "cms_name": cms_name,
                'poc_name': vuln_info.get('vuln_name'),
                'type': "poc_log",
                'log_info': str(log_info),
                'log_type': str(log_type)
            }
            self._data.emit(result)
        else:
            result = {"type": "log", "log_info": file_path + " 该模块未找到！"}
            self._data.emit(result)

    def scan_result_out(self, result_dict, vuln_info, poc_info):
        result = {
            "type": "result",
            'result': result_dict.get('Result'),
            'result_info': str(result_dict.get('Result_Info')),
            'url': str(poc_info['url']),
            'poc_file': str(poc_info['path']),
            'cms_name': str(poc_info.get('cms_name')),
            'poc_name': str(vuln_info.get('vuln_name'))
        }
        self._data.emit(result)

    def port_scanner(self, host, port, timeout):
        # 返回0不存活 1存活
        try:
            tcp = socket(AF_INET, SOCK_STREAM)
            tcp.settimeout(int(timeout))  # 如果设置太小，检测不精确，设置太大，检测太慢
            # print(host,port)
            result = tcp.connect_ex((host, int(port)))  # 效率比connect高，成功时返回0，失败时返回错误码
            # print(port+"success")
            if result == 0:
                return 1
            else:
                return 0
        except Exception as e:
            self.logger.error(str(e) + '----' + str(e.__traceback__.tb_lineno) + '行')
            return 0
        finally:
            try:
                tcp.close()
            except:
                pass
