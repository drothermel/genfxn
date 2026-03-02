public final class Main {
$method_code
    private static long[] parseLongArray(String raw) {
        if (raw == null || raw.isEmpty()) {
            return new long[0];
        }
        String[] parts = raw.split(",");
        long[] out = new long[parts.length];
        for (int i = 0; i < parts.length; i++) {
            out[i] = Long.parseLong(parts[i]);
        }
        return out;
    }

    private static int[] parseIntArray(String raw) {
        if (raw == null || raw.isEmpty()) {
            return new int[0];
        }
        String[] parts = raw.split(",");
        int[] out = new int[parts.length];
        for (int i = 0; i < parts.length; i++) {
            out[i] = Integer.parseInt(parts[i]);
        }
        return out;
    }

    private static long[][] parseIntervals(String raw) {
        if (raw == null || raw.isEmpty()) {
            return new long[0][2];
        }
        String[] parts = raw.split(",");
        long[][] out = new long[parts.length][2];
        for (int i = 0; i < parts.length; i++) {
            String[] pair = parts[i].split(":", 2);
            if (pair.length < 2) {
                throw new IllegalArgumentException(
                    "Invalid interval token '" + parts[i] + "' (expected start:end)"
                );
            }
            out[i][0] = Long.parseLong(pair[0]);
            out[i][1] = Long.parseLong(pair[1]);
        }
        return out;
    }

    public static void main(String[] args) {
$main_body
    }
}
