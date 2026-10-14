package com.example.socker.exception;

import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * 全局异常处理器
 * ==============
 * 统一把异常转换成前端约定的 {code, message, data} 结构。
 *
 * 解决的问题：初版没有任何异常处理，Python 服务未启动时 Spring 会返回
 * 默认的 HTML 错误页，前端 axios 解析失败，用户只看到"网络错误"，
 * 完全无法判断是哪一层出的问题。
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * Python 服务返回 4xx / 5xx：透传原始状态码与响应体。
     *
     * 例如球员不存在（Python 返回 404），前端应拿到 404 语义与
     * Python 自己的 {code, message}，而不是被统一包装成 500。
     */
    @ExceptionHandler(PythonServiceException.class)
    public ResponseEntity<String> handlePythonService(PythonServiceException e,
                                                     HttpServletRequest request) {
        log.warn("分析服务返回错误 [{} {}] status={} message={}",
                request.getMethod(), request.getRequestURI(),
                e.getUpstreamStatus(), e.getMessage());

        String body = e.getUpstreamBody();

        // Python 返回的已经是 {code, message, data} 结构 -> 原样透传，零信息损失
        if (StringUtils.hasText(body) && body.trim().startsWith("{")) {
            return ResponseEntity.status(e.upstreamHttpStatus())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body);
        }

        return buildResponse(
                e.upstreamHttpStatus(),
                StringUtils.hasText(body) ? body : "分析服务返回错误");
    }

    /**
     * Python 服务不可达（未启动 / 超时 / 连接被拒）。返回 503 并给出明确排查提示。
     */
    @ExceptionHandler(PythonServiceUnavailableException.class)
    public ResponseEntity<String> handleUnavailable(PythonServiceUnavailableException e,
                                                   HttpServletRequest request) {
        log.error("分析服务不可达 [{} {}]: {}",
                request.getMethod(), request.getRequestURI(), e.getMessage());

        return buildResponse(
                HttpStatus.SERVICE_UNAVAILABLE,
                "分析服务暂时不可用，请确认 Python 服务已启动（默认 127.0.0.1:5000）");
    }

    /**
     * 兜底：RestClient 直接抛出的连接类异常（正常会被 PythonApiClient 包装，
     * 此处保留以覆盖未被包装的调用路径）。
     */
    @ExceptionHandler(ResourceAccessException.class)
    public ResponseEntity<String> handleResourceAccess(ResourceAccessException e,
                                                      HttpServletRequest request) {
        log.error("HTTP 调用失败 [{} {}]: {}",
                request.getMethod(), request.getRequestURI(), e.getMessage());

        return buildResponse(
                HttpStatus.SERVICE_UNAVAILABLE,
                "无法连接下游服务或请求超时，请检查 Python 分析服务状态");
    }

    /**
     * 兜底：其余未预期异常。
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<String> handleOther(Exception e,
                                             HttpServletRequest request) {
        log.error("未预期异常 [{} {}]", request.getMethod(), request.getRequestURI(), e);

        return buildResponse(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "后端服务内部错误：" + e.getClass().getSimpleName());
    }

    /**
     * 访问了不存在的接口路径。
     *
     * 必须单独处理：否则会被上面的 Exception 兜底吞掉并报成 500 ——
     * 把"路径写错了"误报成"服务端故障"，会严重误导排查方向。
     */
    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<String> handleNoResource(NoResourceFoundException e,
                                                  HttpServletRequest request) {
        log.warn("接口不存在 [{} {}]", request.getMethod(), request.getRequestURI());

        return buildResponse(
                HttpStatus.NOT_FOUND,
                "接口不存在：" + request.getMethod() + " " + request.getRequestURI());
    }

    /**
     * HTTP 方法不被支持（如对只支持 GET 的接口发 POST）。
     */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<String> handleMethodNotSupported(HttpRequestMethodNotSupportedException e,
                                                          HttpServletRequest request) {
        log.warn("请求方法不支持 [{} {}]: {}",
                request.getMethod(), request.getRequestURI(), e.getMessage());

        return buildResponse(
                HttpStatus.METHOD_NOT_ALLOWED,
                "接口不支持 " + request.getMethod() + " 方法");
    }

    /**
     * 请求参数类型不匹配（如把 page 传成非数字）。
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<String> handleTypeMismatch(MethodArgumentTypeMismatchException e,
                                                    HttpServletRequest request) {
        log.warn("参数类型错误 [{} {}]: {}",
                request.getMethod(), request.getRequestURI(), e.getMessage());

        return buildResponse(
                HttpStatus.BAD_REQUEST,
                "参数 " + e.getName() + " 的取值非法");
    }

    /**
     * 构造与 Python 端一致的统一响应体（手写 JSON，避免为此引入序列化依赖）。
     *
     * 参数用 HttpStatusCode 而非 HttpStatus：上游状态码可能是任意 4xx/5xx，
     * HttpStatusCode.valueOf() 返回的是接口类型，不能强转为枚举。
     */
    private ResponseEntity<String> buildResponse(HttpStatusCode status, String message) {
        int code = status.value();

        String json = "{\"code\":" + code
                + ",\"message\":" + quote(message)
                + ",\"data\":null}";

        return ResponseEntity.status(status)
                .contentType(MediaType.APPLICATION_JSON)
                .body(json);
    }

    /** 最小化的 JSON 字符串转义 */
    private String quote(String raw) {
        if (raw == null) {
            return "null";
        }
        StringBuilder sb = new StringBuilder(raw.length() + 2);
        sb.append('"');
        for (char c : raw.toCharArray()) {
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
                }
            }
        }
        sb.append('"');
        return sb.toString();
    }
}
