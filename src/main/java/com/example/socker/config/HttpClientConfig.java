package com.example.socker.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;

/**
 * HTTP 客户端配置
 * ===============
 * 为调用 Python 分析服务的 RestClient 配置连接 / 读取超时。
 *
 * ⚠️ 不配超时的后果：Python 端的聚类、PCA、模型推理一旦卡住，
 * Java 线程会无限等待，并发几个请求就会耗尽 Tomcat 线程池导致整个服务假死。
 *
 * 超时取值依据：
 * - 连接超时 5s：Python 服务启动时会同步训练 4 个位置的随机森林模型
 *   （300 棵树 + 5 折交叉验证），首次启动需数秒，留出余量。
 * - 读取超时 30s：查询基于内存数据，正常毫秒级返回；
 *   30s 覆盖冷启动后的首批请求，同时避免请求无限挂起。
 */
@Configuration
public class HttpClientConfig {

    /** 建连超时（秒） */
    public static final int CONNECT_TIMEOUT_SECONDS = 5;

    /** 读取超时（秒） */
    public static final int READ_TIMEOUT_SECONDS = 30;

    /**
     * 统一的请求工厂。所有对外 HTTP 客户端都应复用它，
     * 避免出现"某个客户端没配超时"的漏网之鱼。
     */
    @Bean
    public ClientHttpRequestFactory clientHttpRequestFactory() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(CONNECT_TIMEOUT_SECONDS));
        factory.setReadTimeout(Duration.ofSeconds(READ_TIMEOUT_SECONDS));
        return factory;
    }

    /**
     * 专用于访问 Python 分析服务的客户端。
     * 默认不抛异常，由 PythonApiClient 通过 exchange 自行处理状态码，
     * 以便把 Python 的 {code, message} 原样透传给前端。
     */
    @Bean
    public RestClient pythonRestClient(
            PythonApiProperties properties,
            ClientHttpRequestFactory clientHttpRequestFactory) {
        return RestClient.builder()
                .baseUrl(properties.getBaseUrl())
                .requestFactory(clientHttpRequestFactory)
                .build();
    }
}
