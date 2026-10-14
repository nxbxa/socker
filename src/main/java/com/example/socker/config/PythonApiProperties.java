package com.example.socker.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Python 分析服务配置
 * ===================
 * 把服务地址从硬编码常量改为外部配置，换机器 / 换端口 / 上 Docker 时
 * 只需改 application.properties，无需改代码重新编译。
 *
 * 配置项见 src/main/resources/application.properties 的 python.api.*
 */
@Component
@ConfigurationProperties(prefix = "python.api")
public class PythonApiProperties {

    /** Python 分析服务基地址，如 http://127.0.0.1:5000 */
    private String baseUrl = "http://127.0.0.1:5000";

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }
}
