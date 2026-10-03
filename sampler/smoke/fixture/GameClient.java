package fixture;

public final class GameClient {
    private int calls;

    public void renderFrame(boolean ignored) {
        calls++;
        try {
            Thread.sleep(40L);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    public boolean isWindowActive() {
        return calls % 5 != 0;
    }
}
