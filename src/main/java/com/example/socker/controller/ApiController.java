package com.example.socker.controller;

import com.example.socker.client.PythonApiClient;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 统一转发层
 * ==========
 * 把前端请求转发给 Python 分析服务，前端只需访问 8080，无需感知 5000 的存在。
 *
 * 设计说明：
 * - 全部返回 ResponseEntity&lt;String&gt; 并显式声明 Content-Type: application/json，
 *   避免 String 返回值被 StringHttpMessageConverter 协商成 text/plain
 *   （中文球员名一旦走错编码就会出现乱码）
 * - 业务错误（如球员不存在）由 GlobalExceptionHandler 统一处理，
 *   本层不写 try/catch，保持职责单一
 */
@RestController
@RequestMapping("/api")
public class ApiController {

    private final PythonApiClient client;

    public ApiController(PythonApiClient client) {
        this.client = client;
    }

    /** 1. 健康检查（服务状态 + 数据规模） */
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return json(client.get("/api/health", null));
    }

    /** 2. 球员列表（page/page_size/position/club/search/order/direction 全部透传） */
    @GetMapping("/players")
    public ResponseEntity<String> players(@RequestParam Map<String, String> params) {
        return json(client.get("/api/players", params));
    }

    /** 3. 球员详情（similar_n 可控制相似球员数量，需经此处透传） */
    @GetMapping("/players/{name}")
    public ResponseEntity<String> playerDetail(
            @PathVariable("name") String name,
            @RequestParam Map<String, String> params) {
        return json(client.get("/api/players/" + name, params));
    }

    /** 4. 各位置评分排行榜 */
    @GetMapping("/rankings")
    public ResponseEntity<String> rankings(@RequestParam Map<String, String> params) {
        return json(client.get("/api/rankings", params));
    }

    /** 5. 聚类分型结果 */
    @GetMapping("/clusters")
    public ResponseEntity<String> clusters(@RequestParam Map<String, String> params) {
        return json(client.get("/api/clusters", params));
    }

    /** 6. 相似球员推荐 */
    @GetMapping("/similar")
    public ResponseEntity<String> similar(@RequestParam Map<String, String> params) {
        return json(client.get("/api/similar", params));
    }

    /** 7. 球员雷达图对比 */
    @GetMapping("/compare")
    public ResponseEntity<String> compare(@RequestParam Map<String, String> params) {
        return json(client.get("/api/compare", params));
    }

    /** 8. 预测模型评估结果 */
    @GetMapping("/models")
    public ResponseEntity<String> models() {
        return json(client.get("/api/models", null));
    }

    /** 9. 评分预测（POST，JSON 请求体原样转发） */
    @PostMapping("/predict")
    public ResponseEntity<String> predict(@RequestBody String body) {
        return json(client.post("/api/predict", body));
    }

    /** 10. 看板汇总数据 */
    @GetMapping("/dashboard")
    public ResponseEntity<String> dashboard() {
        return json(client.get("/api/dashboard", null));
    }

    /** 11. 元信息（指标中文标签 / 权重 / 雷达维度） */
    @GetMapping("/meta")
    public ResponseEntity<String> meta() {
        return json(client.get("/api/meta", null));
    }

    /**
     * 统一包装：声明 JSON 内容类型。
     */
    private ResponseEntity<String> json(String body) {
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .body(body);
    }
}
