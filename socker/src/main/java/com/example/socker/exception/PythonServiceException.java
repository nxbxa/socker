package com.example.socker.exception;

import org.springframework.http.HttpStatusCode;

/**
 * Python 分析服务返回错误状态码（4xx / 5xx）时抛出。
 *
 * 携带上游的原始状态码与响应体，便于全局异常处理器把
 * Python 的 {code, message} 原样透传给前端，而不是包装成 500 白页。
 */
public class PythonServiceException extends RuntimeException {

    /** Python 端返回的 HTTP 状态码 */
    private final int upstreamStatus;

    /** Python 端返回的原始响应体（JSON 文本） */
    private final String upstreamBody;

    public PythonServiceException(int upstreamStatus, String upstreamBody, String message) {
        super(message);
        this.upstreamStatus = upstreamStatus;
        this.upstreamBody = upstreamBody;
    }

    public int getUpstreamStatus() {
        return upstreamStatus;
    }

    public String getUpstreamBody() {
        return upstreamBody;
    }

    /** 上游状态码转 Spring 的 HttpStatusCode */
    public HttpStatusCode upstreamHttpStatus() {
        return HttpStatusCode.valueOf(upstreamStatus);
    }
}
