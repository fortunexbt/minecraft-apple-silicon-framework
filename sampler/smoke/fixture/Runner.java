package fixture;

public final class Runner {
    public static void main(String[] args) throws Exception {
        long runMillis = args.length == 0 ? 7000L : Long.parseLong(args[0]);
        GameClient client = new GameClient();
        long end = System.nanoTime() + runMillis * 1000000L;
        while (System.nanoTime() < end) client.renderFrame(false);
    }
}
