import java.util.*;

class Post implements Comparable<Post> {
    String postId;
    String authorId;
    long timestampMs;
    int likes;
    int shares;
    double score;

    public Post(String postId, String authorId, long timestampMs, int likes, int shares) {
        this.postId = postId;
        this.authorId = authorId;
        this.timestampMs = timestampMs;
        this.likes = likes;
        this.shares = shares;
        this.score = computeScore();
    }

    public final double computeScore() {
        double engagement = (likes * 0.4) + (shares * 0.6);
        double hoursOld = (System.currentTimeMillis() - timestampMs) / (1000.0 * 60 * 60);
        return engagement / Math.pow(hoursOld + 2, 1.5);
    }

    @Override
    public int compareTo(Post other) {
        return Double.compare(other.score, this.score);
    }
}

public class SocialFeedEngine {
    private static final int CELEBRITY_THRESHOLD = 5; // Simplified threshold for testing

    private final Map<String, List<String>> followersMap = new HashMap<>();
    private final Map<String, List<Post>> celebrityPostsMap = new HashMap<>(); // Pull model storage
    private final Map<String, List<Post>> userInboxesMap = new HashMap<>();     // Push model pre-computed feeds

    public void addFollower(String followerId, String targetId) {
        followersMap.putIfAbsent(targetId, new ArrayList<>());
        followersMap.get(targetId).add(followerId);
    }

    // Hybrid Fan-Out Routing Strategy
    public void publishPost(String authorId, String postId, int likes, int shares, long hoursAgo) {
        long timestamp = System.currentTimeMillis() - (hoursAgo * 60 * 60 * 1000);
        Post post = new Post(postId, authorId, timestamp, likes, shares);

        List<String> followers = followersMap.getOrDefault(authorId, Collections.emptyList());

        if (followers.size() >= CELEBRITY_THRESHOLD) {
            // PULL MODEL: Store in author's outbox. Don't push to millions of inboxes.
            celebrityPostsMap.putIfAbsent(authorId, new ArrayList<>());
            celebrityPostsMap.get(authorId).add(post);
        } else {
            // PUSH MODEL: Instantly fan-out to all active followers' inboxes
            for (String follower : followers) {
                userInboxesMap.putIfAbsent(follower, new ArrayList<>());
                userInboxesMap.get(follower).add(post);
            }
        }
    }

    // Generates Feed combining Pushed Inbox Items + Pulled Celebrity Posts via Max-Heap
    public List<String> generateFeed(String userId, List<String> followingList, int k) {
        PriorityQueue<Post> feedHeap = new PriorityQueue<>();

        // 1. Fetch pre-computed inbox posts (Push Model)
        List<Post> inboxPosts = userInboxesMap.getOrDefault(userId, Collections.emptyList());
        for (Post p : inboxPosts) {
            p.score = p.computeScore();
            feedHeap.add(p);
        }

        // 2. Dynamically pull celebrity posts at read-time (Pull Model)
        for (String target : followingList) {
            if (celebrityPostsMap.containsKey(target)) {
                for (Post p : celebrityPostsMap.get(target)) {
                    p.score = p.computeScore();
                    feedHeap.add(p);
                }
            }
        }

        // 3. Extract Top-K ranked timeline items
        List<String> feed = new ArrayList<>();
        int count = 0;
        while (!feedHeap.isEmpty() && count < k) {
            Post top = feedHeap.poll();
            feed.add(String.format("PostID: %s | Author: %s | Score: %.2f", top.postId, top.authorId, top.score));
            count++;
        }

        return feed;
    }

    public static void main(String[] args) {
        SocialFeedEngine engine = new SocialFeedEngine();

        // Setup Followers (Make "TechCrunch" a Celebrity with 5+ followers)
        for (int i = 1; i <= 6; i++) {
            engine.addFollower("User_" + i, "TechCrunch");
        }
        engine.addFollower("User_1", "RegularUser"); // Regular creator

        // Publish Posts
        engine.publishPost("RegularUser", "Post_Regular", 50, 5, 0);   // Pushed to User_1 Inbox
        engine.publishPost("TechCrunch", "Post_Celebrity", 10000, 2000, 1); // Pulled at Read Time

        // Generate Feed for User_1
        System.out.println("=== Hybrid Push/Pull Dynamic Social Feed ===");
        List<String> userFeed = engine.generateFeed("User_1", Arrays.asList("TechCrunch", "RegularUser"), 5);

        for (int i = 0; i < userFeed.size(); i++) {
            System.out.println((i + 1) + ". " + userFeed.get(i));
        }
    }
}