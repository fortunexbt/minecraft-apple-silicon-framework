// SPDX-License-Identifier: MIT
import java.nio.file.*;
import java.util.zip.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
public class RenderScaleStraightPatch {
 public static void main(String[] args) throws Exception {
  int edits=0;
  try (ZipFile input=new ZipFile(args[0]); ZipOutputStream output=new ZipOutputStream(Files.newOutputStream(Path.of(args[1])))) {
   var entries=input.entries();
   while(entries.hasMoreElements()) {
    var entry=entries.nextElement(); byte[] data=input.getInputStream(entry).readAllBytes();
    if(entry.getName().equals("dev/zelo/renderscale/RenderScale.class")) {
     ClassNode node=new ClassNode(); new ClassReader(data).accept(node,0);
     for(MethodNode method:node.methods) if(method.name.equals("updateDynamicScale") && method.desc.equals("()V")) {
      for(AbstractInsnNode instruction:method.instructions.toArray()) if(instruction instanceof MethodInsnNode call && call.owner.equals("dev/zelo/renderscale/DynamicScaleController") && call.name.equals("update") && call.desc.equals("(JIIDDZ)Z")) {
       var previous=instruction.getPrevious();
       while(previous!=null && previous.getOpcode()<0) previous=previous.getPrevious();
       if(!(previous instanceof VarInsnNode variable) || variable.getOpcode()!=Opcodes.ILOAD || variable.var!=7) throw new IllegalStateException("Unexpected dynamic update argument");
       method.instructions.set(previous,new InsnNode(Opcodes.ICONST_1)); edits++;
      }
     }
     if(edits!=1) throw new IllegalStateException("Expected one edit, got "+edits);
     ClassWriter writer=new ClassWriter(0);node.accept(writer);data=writer.toByteArray();
    }
    output.putNextEntry(new ZipEntry(entry.getName()));output.write(data);output.closeEntry();
   }
  }
  if(edits!=1)throw new IllegalStateException("Missing class");
  System.out.println("Patched one boolean argument; existing guards/controller unchanged");
 }
}
