package com.example.apidiff;


import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.module.SimpleModule;
import com.fasterxml.jackson.databind.ser.std.StdSerializer;

import java.io.IOException;
import java.util.IdentityHashMap;
import java.util.Map;

public class CircularReferenceModule extends SimpleModule {
    public CircularReferenceModule() {
        super("CircularReferenceModule");
        this.addSerializer(Object.class, new CircularReferenceSerializer<>(Object.class));
    }
}
