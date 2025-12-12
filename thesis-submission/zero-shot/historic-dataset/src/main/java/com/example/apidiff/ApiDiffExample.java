package com.example.apidiff;

import apidiff.APIDiff;
import apidiff.Change;
import apidiff.Result;
import apidiff.enums.Classifier;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.ser.impl.SimpleBeanPropertyFilter;
import com.fasterxml.jackson.databind.ser.impl.SimpleFilterProvider;
import org.eclipse.jgit.api.Git;
import org.eclipse.jgit.api.LsRemoteCommand;
import org.eclipse.jgit.api.errors.GitAPIException;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.lib.Ref;
import org.eclipse.jgit.revwalk.RevCommit;
import org.eclipse.jgit.revwalk.RevWalk;
import org.eclipse.jgit.transport.URIish;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class ApiDiffExample {

    public static void main(String[] args) {
        String repoUrl = "https://github.com/spring-projects/spring-boot.git";
        String localRepoPath = "/Users/anon/Projects/masterthesis/historic-dataset/train/spring-boot/spring-boot";
        String projectName = "spring-projects/spring-boot";

        try {
            // List remote tags
            List<Ref> tags = listRemoteTags(repoUrl);
            System.out.println("Found " + tags.size() + " tags.");

            // Sort tags by commit time
            Collections.sort(tags, (tag1, tag2) -> {
                try {
                    ObjectId commit1 = tag1.getObjectId();
                    ObjectId commit2 = tag2.getObjectId();
                    return commit1.name().compareTo(commit2.name());
                } catch (Exception e) {
                    e.printStackTrace();
                    return 0;
                }
            });

            // Configure the ObjectMapper
            ObjectMapper mapper = configureMapper();

            APIDiff diff = new APIDiff(projectName, repoUrl);
                    diff.setPath(localRepoPath);

            // Process commits between each pair of tags
            for (int i = 0; i < tags.size() - 1; i++) {
                Ref tag1 = tags.get(i);
                Ref tag2 = tags.get(i + 1);
                System.out.println("Processing commits between: " + tag1.getName() + " and " + tag2.getName());

                List<RevCommit> commits = listCommitsBetweenTags(repoUrl, tag1, tag2);

                for (RevCommit commit : commits) {
                    String commitHash = commit.getName();
                    System.out.println("Processing commit: " + commitHash);



                    Result result = diff.detectChangeAtCommit(commitHash, Classifier.API);

                    Map<String, List<Change>> changesGroupedByRevCommit = result.getChangeMethod().stream()
                            .collect(Collectors.groupingBy(change -> change.getRevCommit().toObjectId().getName()));

                    for (Map.Entry<String, List<Change>> entry : changesGroupedByRevCommit.entrySet()) {
                        String revCommitId = entry.getKey();
                        List<Change> changes = entry.getValue();

                        try {
                            mapper.writeValue(
                                    new File(localRepoPath + "/" + revCommitId + ".json"),
                                    changes);
                            System.out.println("Changes written to " + revCommitId + ".json");
                        } catch (IOException e) {
                            e.printStackTrace();
                        }

                        for (Change change : changes) {
                            System.out.println(
                                    "\n" + change.getCategory().getDisplayName() + " - " + change.getDescription());
                        }
                    }
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static List<Ref> listRemoteTags(String repoUrl) throws GitAPIException {
        LsRemoteCommand lsRemote = Git.lsRemoteRepository().setRemote(repoUrl).setTags(true);
        return new ArrayList<>(lsRemote.call());
    }

    private static List<RevCommit> listCommitsBetweenTags(String repoUrl, Ref tag1, Ref tag2) throws IOException, GitAPIException {
        try (Git git = Git.lsRemoteRepository().setRemote(repoUrl).setHeads(true).call()) {
            ObjectId startCommit = tag1.getObjectId();
            ObjectId endCommit = tag2.getObjectId();

            try (RevWalk walk = new RevWalk(git.getRepository())) {
                walk.markStart(walk.parseCommit(endCommit));
                walk.markUninteresting(walk.parseCommit(startCommit));

                List<RevCommit> commits = new ArrayList<>();
                for (RevCommit commit : walk) {
                    commits.add(commit);
                }
                return commits;
            }
        }
    }

    private static ObjectMapper configureMapper() {
        ObjectMapper mapper = new ObjectMapper();

        // Register the mixin
        mapper.addMixIn(Change.class, ChangeMixin.class);

        // Define which properties to include
        SimpleFilterProvider filters = new SimpleFilterProvider()
                .addFilter("ChangeFilter", SimpleBeanPropertyFilter.filterOutAllExcept(
                        "path", "element", "category", "breakingChange", "description",
                        "javadoc", "deprecated", "elementType"));

        // Apply the filter to the ObjectMapper
        mapper.setFilterProvider(filters);

        // Optionally configure other settings
        mapper.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);
        mapper.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);

        return mapper;
    }
}
