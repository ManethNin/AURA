package com.example.apidiff;


import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.module.SimpleModule;
import com.fasterxml.jackson.databind.ser.std.StdSerializer;

import java.io.IOException;
import java.util.IdentityHashMap;
import java.util.Map;

public class CircularReferenceSerializer<T> extends StdSerializer<T> {

    private static final Map<Object, Boolean> serializedObjects = new IdentityHashMap<>();

    public CircularReferenceSerializer(Class<T> t) {
        super(t);
    }

    @Override
    public void serialize(T value, JsonGenerator gen, SerializerProvider provider) throws IOException {
        if (serializedObjects.containsKey(value)) {
            gen.writeNull(); // Skip serialization
        } else {
            serializedObjects.put(value, Boolean.TRUE);
            gen.writeStartObject();
            gen.writeObjectField("id", value.hashCode()); // Example logic to serialize object
            // Add other fields here
            gen.writeEndObject();
        }
    }
}
