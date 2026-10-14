package com.example.socker.exception;

/**
 * Python 分析服务不可达（未启动 / 连接被拒 / 超时）时抛出。
 *
 * 这是最常见的开发期故障：忘了先启动 Flask 服务。
 * 单独建一个异常类型，是为了让全局处理器返回 503 与明确的排查提示，
 * 而不是抛出一个信息量极低的 500。
 */
public class PythonServiceUnavailableException extends RuntimeException {

    public PythonServiceUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}
