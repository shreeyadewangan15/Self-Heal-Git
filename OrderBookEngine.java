import java.util.*;

class LimitOrder {
    String orderId;
    String symbol;
    boolean isBuyOrder;
    double price;
    int quantity;
    long timestamp;

    public LimitOrder(String orderId, String symbol, boolean isBuyOrder, double price, int quantity) {
        this.orderId = orderId;
        this.symbol = symbol;
        this.isBuyOrder = isBuyOrder;
        this.price = price;
        this.quantity = quantity;
        this.timestamp = System.nanoTime();
    }
}

// Real-Time Analytics calculating streaming Volatility (Welford's Algorithm) and EMA
class StockAnalyticsEngine {
    private int count = 0;
    private double mean = 0.0;
    private double M2 = 0.0; // Sum of squared differences
    private double ema = 0.0;
    private final double alpha = 0.2; // Smoothing factor for EMA

    public void ingestExecutedPrice(double price) {
        count++;
        // 1. Calculate Streaming Mean and Standard Deviation in O(1) Memory
        double delta = price - mean;
        mean += delta / count;
        double delta2 = price - mean;
        M2 += delta * delta2;

        // 2. Calculate Exponential Moving Average (EMA)
        if (count == 1) {
            ema = price;
        } else {
            ema = (price * alpha) + (ema * (1 - alpha));
        }
    }

    public double getStandardDeviation() {
        return count > 1 ? Math.sqrt(M2 / (count - 1)) : 0.0;
    }

    public double getEMA() {
        return ema;
    }
}

public class OrderBookEngine {
    private final PriorityQueue<LimitOrder> buyBids = new PriorityQueue<>((a, b) -> {
        if (Double.compare(b.price, a.price) != 0) return Double.compare(b.price, a.price);
        return Long.compare(a.timestamp, b.timestamp);
    });

    private final PriorityQueue<LimitOrder> sellAsks = new PriorityQueue<>((a, b) -> {
        if (Double.compare(a.price, b.price) != 0) return Double.compare(a.price, b.price);
        return Long.compare(a.timestamp, b.timestamp);
    });

    private final Map<String, LimitOrder> activeOrdersMap = new HashMap<>();
    private final StockAnalyticsEngine analyticsEngine = new StockAnalyticsEngine();

    public void submitOrder(LimitOrder incomingOrder) {
        if (incomingOrder.isBuyOrder) {
            matchBuyOrder(incomingOrder);
        } else {
            matchSellOrder(incomingOrder);
        }

        if (incomingOrder.quantity > 0) {
            if (incomingOrder.isBuyOrder) buyBids.add(incomingOrder);
            else sellAsks.add(incomingOrder);
            activeOrdersMap.put(incomingOrder.orderId, incomingOrder);
        }
    }

    private void matchBuyOrder(LimitOrder buyOrder) {
        while (!sellAsks.isEmpty() && sellAsks.peek().price <= buyOrder.price && buyOrder.quantity > 0) {
            LimitOrder topAsk = sellAsks.peek();
            int executedQty = Math.min(buyOrder.quantity, topAsk.quantity);

            buyOrder.quantity -= executedQty;
            topAsk.quantity -= executedQty;

            System.out.println(String.format("    [EXECUTION] %d shares @ $%.2f", executedQty, topAsk.price));
            analyticsEngine.ingestExecutedPrice(topAsk.price); // Feed live price to analytics engine

            if (topAsk.quantity == 0) {
                sellAsks.poll();
                activeOrdersMap.remove(topAsk.orderId);
            }
        }
    }

    private void matchSellOrder(LimitOrder sellOrder) {
        while (!buyBids.isEmpty() && buyBids.peek().price >= sellOrder.price && sellOrder.quantity > 0) {
            LimitOrder topBid = buyBids.peek();
            int executedQty = Math.min(sellOrder.quantity, topBid.quantity);

            sellOrder.quantity -= executedQty;
            topBid.quantity -= executedQty;

            System.out.println(String.format("    [EXECUTION] %d shares @ $%.2f", executedQty, sellOrder.price));
            analyticsEngine.ingestExecutedPrice(sellOrder.price); // Feed live price to analytics engine

            if (topBid.quantity == 0) {
                buyBids.poll();
                activeOrdersMap.remove(topBid.orderId);
            }
        }
    }

    public void printMarketAnalytics() {
        System.out.println(String.format("=== Real-Time Analytics | EMA: $%.2f | Volatility (StdDev): $%.4f ===",
                analyticsEngine.getEMA(), analyticsEngine.getStandardDeviation()));
    }

    public static void main(String[] args) {
        OrderBookEngine engine = new OrderBookEngine();

        // 1. Seed Ask Liquidity
        engine.submitOrder(new LimitOrder("ASK_1", "GOOGL", false, 170.00, 10));
        engine.submitOrder(new LimitOrder("ASK_2", "GOOGL", false, 172.50, 20));
        engine.submitOrder(new LimitOrder("ASK_3", "GOOGL", false, 175.00, 15));

        // 2. Submit Buy Orders triggering dynamic executions across price tiers
        System.out.println("\n--- Order Match Batch 1 ---");
        engine.submitOrder(new LimitOrder("BUY_1", "GOOGL", true, 173.00, 25));
        engine.printMarketAnalytics();

        System.out.println("\n--- Order Match Batch 2 ---");
        engine.submitOrder(new LimitOrder("BUY_2", "GOOGL", true, 180.00, 15));
        engine.printMarketAnalytics();
    }
}