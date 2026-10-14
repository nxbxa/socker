package com.example.socker.client;

import com.example.socker.exception.PythonServiceException;
import com.example.socker.exception.PythonServiceUnavailableException;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.util.Map;

/**
 * Python 分析服务客户端
 * =====================
 * 负责调用 Flask 提供的 11 个数据分析接口。
 *
 * 相比初版的关键改进：
 * 1. 使用 RestClient（Spring 官方推荐的现代 HTTP 客户端）替代 RestTemplate
 * 2. 超时由 HttpClientConfig 统一配置，不再出现无限等待
 * 3. 显式捕获连接失败 / 超时，区分"服务没启动"与"业务错误"
 * 4. 服务地址来自 PythonApiProperties（可外部配置）
 */
@Component
public class PythonApiClient {

    private final RestClient client;

    public PythonApiClient(RestClient pythonRestClient) {
        this.client = pythonRestClient;
    }

    /**
     * 发送 GET 请求（支持查询参数透传）。
     *
     * @param path   接口路径，如 "/api/players"
     * @param params 查询参数（可为 null），自动过滤空值
     * @return Python 端返回的 JSON 文本
     */
    public String get(String path, Map<String, String> params) {
        return execute(buildUri(path, params), null);
    }

    /**
     * 发送 POST 请求（JSON 请求体原样转发）。
     */
    public String post(String path, String jsonBody) {
        return execute(buildUri(path, null), jsonBody);
    }

    /**
     * 拼接查询参数。
     *
     * 注意：encode() 会把空格编码为 %20（而非 +），Flask 两种都能正确解析；
     * 中文球员名与带重音符号的姓名（如 Mbappé、Kanté）也能安全传输。
     */
    private URI buildUri(String path, Map<String, String> params) {
        UriComponentsBuilder builder = UriComponentsBuilder.fromPath(path);

        if (params != null) {
            params.forEach((key, value) -> {
                if (StringUtils.hasText(value)) {
                    builder.queryParam(key, value);
                }
            });
        }

        return builder.build().encode().toUri();
    }

    /**
     * 统一执行请求并把底层异常映射为业务异常。
     *
     * @param uri      目标地址（相对 baseUrl）
     * @param jsonBody POST 请求体；为 null 时执行 GET
     */
    private String execute(URI uri, String jsonBody) {
        HttpMethod method = jsonBody == null ? HttpMethod.GET : HttpMethod.POST;

        try {
            RestClient.RequestBodySpec spec = client
                    .method(method)
                    .uri(uri)
                    .accept(MediaType.APPLICATION_JSON);

            RestClient.ResponseSpec responseSpec = jsonBody == null
                    ? spec.retrieve()
                    : spec.contentType(MediaType.APPLICATION_JSON)
                          .body(jsonBody)
                          .retrieve();

            String body = responseSpec.body(String.class);
            return body == null ? "{}" : body;

        } catch (RestClientResponseException e) {
            // Python 返回 4xx / 5xx：把它自己的 {code, message} 原样透传，
            // 而不是包装成 Java 的 500（"未找到球员：xxx" 应保持 404 语义）
            throw new PythonServiceException(
                    e.getStatusCode().value(),
                    e.getResponseBodyAsString(),
                    "分析服务返回错误：" + e.getStatusCode().value());

        } catch (ResourceAccessException e) {
            // 连接被拒 / 读超时 / DNS 失败 —— 最常见的"忘了启动 Flask"
            throw new PythonServiceUnavailableException(
                    "无法连接 Python 分析服务，请确认它已在配置地址上启动", e);
        }
    }
}
