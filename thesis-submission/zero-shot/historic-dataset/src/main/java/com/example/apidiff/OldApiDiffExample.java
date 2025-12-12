package com.example.apidiff;

import apidiff.APIDiff;
import apidiff.Change;
import apidiff.Result;
import apidiff.enums.Classifier;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import org.eclipse.jgit.api.Git;
import org.eclipse.jgit.api.errors.GitAPIException;
import org.eclipse.jgit.transport.UsernamePasswordCredentialsProvider;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.module.SimpleModule;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.ser.impl.SimpleBeanPropertyFilter;
import com.fasterxml.jackson.databind.ser.impl.SimpleFilterProvider;
import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.io.File;
import java.io.IOException;
import java.util.List;

class DiffEntry {
    public String id;
    public String client;
    public String url;
    public String sha;
    public String lib;
    public String old;
    public String newVersion; // 'new' is a reserved keyword in Java, so using 'newVersion' instead
    public String test;
    public String submodule;
    public String test_cmd;
}

public class OldApiDiffExample {
    public static void main(String[] args) {
        // if (args.length < 1) {
        //     System.out.println("Usage: java -jar apidiff-example.jar <path-to-json-file>");
        //     System.exit(1);
        // }

        // String jsonFilePath = args[0];
        // ObjectMapper mapper = new ObjectMapper();

        // try {
        // List<DiffEntry> diffEntries = mapper.readValue(new File(jsonFilePath), new
        // TypeReference<List<DiffEntry>>(){});
        // for (DiffEntry entry : diffEntries) {
        // processEntry(entry);
        // }
        // } catch (IOException e) {
        // e.printStackTrace();
        // }
        APIDiff diff = new APIDiff("spring-projects/spring-boot", "https://github.com/spring-projects/spring-boot.git");
        diff.setPath("/Users/anon/Projects/masterthesis/historic-dataset/train/spring-boot/spring-boot");

        String commitHash = "b645eb32ac14af60f9acfa6866b20bc9b15e2940";

        try {

            // Result result = diff.detectChangeAllHistory("main", Classifier.API);

            Result result = diff.detectChangeAtCommit(commitHash, Classifier.API);

            ObjectMapper mapper = new ObjectMapper();

            // // Register the custom module to handle circular references
            // SimpleModule circularReferenceModule = new CircularReferenceModule();
            // mapper.registerModule(circularReferenceModule);

            // // Optionally configure other settings
            // mapper.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);
            // mapper.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);

            // Register the mixin
            mapper.addMixIn(Change.class, ChangeMixin.class);

            // Define which properties to include
            SimpleFilterProvider filters = new SimpleFilterProvider()
                    .addFilter("ChangeFilter", SimpleBeanPropertyFilter.filterOutAllExcept(
                            "path",
                            // "element",
                            "category",
                            "breakingChange",
                            "description",
                            "javadoc",
                            "deprecated",
                            "elementType"));

            // Apply the filter to the ObjectMapper
            mapper.setFilterProvider(filters);

            // Optionally configure other settings
            mapper.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);
            mapper.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);

            // Convert the changes to JSON and write it to a file
            // try {
            // mapper.writeValue(new
            // File("/Users/anon/Projects/masterthesis/historic-dataset/train/spring-boot/"+commitHash+".json"),
            // result.getChangeMethod());
            // System.out.println("Changes written to "+commitHash+".json");
            // } catch (IOException e) {
            // e.printStackTrace();
            // }
            // for (Change changeMethod : result.getChangeMethod()) {
            // changeMethod.revCommit.toObjectId().getName()
            // System.out.println(
            // "\n" + changeMethod.getCategory().getDisplayName() + " - " +
            // changeMethod.getDescription());
            // // Create an ObjectMapper to serialize the changes to JSON

            // }

            Map<String, List<Change>> changesGroupedByRevCommit = result.getChangeMethod().stream()
                    .collect(Collectors.groupingBy(change -> change.getRevCommit().toObjectId().getName()));

            System.out.println("Number of commits: " + changesGroupedByRevCommit.size());
            // System.out.println(changesGroupedByRevCommit);

            // System.out.println(result.getChangeMethod());

            for (Map.Entry<String, List<Change>> entry : changesGroupedByRevCommit.entrySet()) {
                String revCommitId = entry.getKey();
                List<Change> changes = entry.getValue();

                try {
                    mapper.writeValue(
                            new File("/Users/anon/Projects/masterthesis/historic-dataset/train/spring-boot/"
                                    + revCommitId + ".json"),
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

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // private static void processEntry(DiffEntry entry) {
    // String localPath = "repos/" + entry.client;

    // try {
    // // Clone the repository if it does not exist locally
    // File localRepoDir = new File(localPath);
    // if (!localRepoDir.exists()) {
    // cloneRepository(entry.url, localPath);
    // }

    // APIDiff diff = new APIDiff(entry.client, entry.url);
    // diff.setPath(localPath);

    // Result result = diff.detectChangeAtCommit(entry.sha, Classifier.API);
    // System.out.println("Changes for entry ID: " + entry.id);
    // for (Change change : result.getChangeMethod()) {
    // System.out.println("\n" + change.getCategory().getDisplayName() + " - " +
    // change.getDescription());
    // }
    // } catch (Exception e) {
    // e.printStackTrace();
    // }
    // }

}
