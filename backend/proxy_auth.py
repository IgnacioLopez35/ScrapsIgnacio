from selenium.webdriver import Chrome, ChromeOptions, ChromeService
from selenium.webdriver import Firefox, FirefoxOptions
from selenium.webdriver import Edge, EdgeOptions

import os
import zipfile

from selenium import webdriver

# proxy_host = '192.168.3.2'  # rotating proxy or host
# proxy_port = 8080 # port
# proxy_user = 'proxy-user' # username
# proxy_pass = 'proxy-password' # password

class ProxyAuth():
    def __init__(self, proxy_host, proxy_port, proxy_user, proxy_pass):
        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
        """

        background_js = """
        var config = {
                mode: "fixed_servers",
                rules: {
                singleProxy: {
                    scheme: "http",
                    host: "%s",
                    port: parseInt(%s)
                },
                bypassList: ["localhost"]
                }
            };

        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "%s",
                    password: "%s"
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {urls: ["<all_urls>"]},
                    ['blocking']
        );
        """ % (proxy_host, proxy_port, proxy_user, proxy_pass)
        
        self.pluginfile = 'proxy_auth_plugin.zip'

        with zipfile.ZipFile(self.pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)

    def get_proxy_extension(self):
        return self.pluginfile