import test.de.ChainClass;

public class TestChainedClass {
    public void testMethod() {
        ChainClass obj = new ChainClass();
        obj.getInner().doSomething();
        obj.getInner()
        .doSomething();

        obj.test();
    }
}
