import java.util.*;

class GraphNode implements Comparable<GraphNode> {
    String id;
    double gScore;
    double fScore;

    public GraphNode(String id, double gScore, double fScore) {
        this.id = id;
        this.gScore = gScore;
        this.fScore = fScore;
    }

    @Override
    public int compareTo(GraphNode other) {
        return Double.compare(this.fScore, other.fScore);
    }
}

class Edge {
    String targetNodeId;
    double baseDistance;
    double trafficMultiplier;

    public Edge(String targetNodeId, double baseDistance) {
        this.targetNodeId = targetNodeId;
        this.baseDistance = baseDistance;
        this.trafficMultiplier = 1.0;
    }

    public double getEffectiveWeight() {
        return baseDistance * trafficMultiplier;
    }
}

public class RouteOptimizerEngine {
    private final Map<String, List<Edge>> adjacencyList = new HashMap<>();
    private final Map<String, double[]> nodeCoordinates = new HashMap<>();

    public void addLocation(String id, double lat, double lon) {
        nodeCoordinates.put(id, new double[]{lat, lon});
        adjacencyList.putIfAbsent(id, new ArrayList<>());
    }

    public void addRoad(String source, String destination, double distance) {
        adjacencyList.get(source).add(new Edge(destination, distance));
        adjacencyList.get(destination).add(new Edge(source, distance));
    }

    public void updateTrafficMultiplier(String source, String destination, double multiplier) {
        updateEdge(source, destination, multiplier);
        updateEdge(destination, source, multiplier);
    }

    private void updateEdge(String source, String destination, double multiplier) {
        List<Edge> edges = adjacencyList.get(source);
        if (edges != null) {
            for (Edge edge : edges) {
                if (edge.targetNodeId.equals(destination)) {
                    edge.trafficMultiplier = multiplier;
                    break;
                }
            }
        }
    }

    private double calculateHeuristic(String node1, String node2) {
        double[] coord1 = nodeCoordinates.get(node1);
        double[] coord2 = nodeCoordinates.get(node2);
        if (coord1 == null || coord2 == null) return 0.0;

        double lat1 = Math.toRadians(coord1[0]);
        double lon1 = Math.toRadians(coord1[1]);
        double lat2 = Math.toRadians(coord2[0]);
        double lon2 = Math.toRadians(coord2[1]);

        double dlat = lat2 - lat1;
        double dlon = lon2 - lon1;

        double a = Math.pow(Math.sin(dlat / 2), 2) + Math.cos(lat1) * Math.cos(lat2) * Math.pow(Math.sin(dlon / 2), 2);
        double c = 2 * Math.asin(Math.sqrt(a));
        return 6371 * c;
    }

    public double getDistanceBetween(String startId, String destinationId) {
        PriorityQueue<GraphNode> openSet = new PriorityQueue<>();
        Map<String, Double> gScores = new HashMap<>();

        gScores.put(startId, 0.0);
        openSet.add(new GraphNode(startId, 0.0, calculateHeuristic(startId, destinationId)));

        while (!openSet.isEmpty()) {
            GraphNode current = openSet.poll();

            if (current.id.equals(destinationId)) {
                return current.gScore;
            }

            for (Edge edge : adjacencyList.getOrDefault(current.id, Collections.emptyList())) {
                double tentativeGScore = gScores.get(current.id) + edge.getEffectiveWeight();

                if (tentativeGScore < gScores.getOrDefault(edge.targetNodeId, Double.MAX_VALUE)) {
                    gScores.put(edge.targetNodeId, tentativeGScore);
                    double fScore = tentativeGScore + calculateHeuristic(edge.targetNodeId, destinationId);
                    openSet.add(new GraphNode(edge.targetNodeId, tentativeGScore, fScore));
                }
            }
        }
        return Double.MAX_VALUE;
    }

    // Solves Multi-Stop Delivery Order (TSP using Greedy Nearest Neighbor)
    public List<String> optimizeMultiStopRoute(String warehouseId, List<String> deliveryStops) {
        List<String> unvisited = new ArrayList<>(deliveryStops);
        List<String> optimizedRoute = new ArrayList<>();

        String current = warehouseId;
        optimizedRoute.add(current);

        while (!unvisited.isEmpty()) {
            String nearest = null;
            double minDistance = Double.MAX_VALUE;

            for (String stop : unvisited) {
                double dist = getDistanceBetween(current, stop);
                if (dist < minDistance) {
                    minDistance = dist;
                    nearest = stop;
                }
            }

            if (nearest != null) {
                optimizedRoute.add(nearest);
                unvisited.remove(nearest);
                current = nearest;
            } else {
                break;
            }
        }

        // Return to warehouse hub to complete tour
        optimizedRoute.add(warehouseId);
        return optimizedRoute;
    }

    public static void main(String[] args) {
        RouteOptimizerEngine optimizer = new RouteOptimizerEngine();

        // 1. Add Locations
        optimizer.addLocation("Warehouse", 19.0760, 72.8777);
        optimizer.addLocation("Customer_1", 19.0850, 72.8900);
        optimizer.addLocation("Customer_2", 19.0950, 72.8700);
        optimizer.addLocation("Customer_3", 19.1100, 72.9000);

        // 2. Add Road Connections
        optimizer.addRoad("Warehouse", "Customer_1", 5.0);
        optimizer.addRoad("Warehouse", "Customer_2", 2.0);
        optimizer.addRoad("Customer_1", "Customer_3", 4.0);
        optimizer.addRoad("Customer_2", "Customer_3", 8.0);
        optimizer.addRoad("Customer_1", "Customer_2", 3.0);
        optimizer.addRoad("Warehouse", "Customer_3", 12.0);

        // 3. Multi-Stop Route Execution
        List<String> stopsToVisit = Arrays.asList("Customer_1", "Customer_3", "Customer_2");
        
        System.out.println("=== E-Commerce Multi-Stop Delivery Optimization ===");
        System.out.println("Unoptimized Stops Requested: " + stopsToVisit);

        List<String> optimizedSequence = optimizer.optimizeMultiStopRoute("Warehouse", stopsToVisit);
        System.out.println("Optimized Driver Route Sequence: " + String.join(" -> ", optimizedSequence));
    }
}