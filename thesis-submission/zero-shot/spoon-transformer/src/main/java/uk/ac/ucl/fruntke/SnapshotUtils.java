package org.coderepair;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class SnapshotUtils {
    private static final String SNAPSHOT_DIR = "src/test/resources/snapshots";
    private static final boolean UPDATE_SNAPSHOTS = Boolean.getBoolean("updateSnapshots");

    public static String getOrUpdateSnapshot(String testName, String actual) throws IOException {
        Path snapshotPath = Paths.get(SNAPSHOT_DIR, testName + ".snap");

        if (UPDATE_SNAPSHOTS) {
            System.out.println("Updating snapshot: " + snapshotPath);
            Files.createDirectories(snapshotPath.getParent());
            Files.writeString(snapshotPath, actual);
            return actual;
        } else {
            if (Files.exists(snapshotPath)) {
                return Files.readString(snapshotPath);
            } else {
                throw new RuntimeException("Snapshot does not exist: " + snapshotPath);
            }
        }
    }
}
