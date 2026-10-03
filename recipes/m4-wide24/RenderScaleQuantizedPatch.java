// SPDX-License-Identifier: MIT
import java.nio.file.*;
import java.util.zip.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
public class RenderScaleQuantizedPatch {
 public static void main(String[] args)throws Exception {
  int edits=0;
  try(ZipFile input=new ZipFile(args[0]);ZipOutputStream output=new ZipOutputStream(Files.newOutputStream(Path.of(args[1])))) {
   var entries=input.entries();while(entries.hasMoreElements()) {
    var e=entries.nextElement();byte[] data=input.getInputStream(e).readAllBytes();
    if(e.getName().equals("dev/zelo/renderscale/RenderScale.class")) {
     ClassNode node=new ClassNode();new ClassReader(data).accept(node,0);
     for(MethodNode method:node.methods) if(method.name.equals("getRenderScaleFactor")&&method.desc.equals("()D")) {
      for(AbstractInsnNode instruction:method.instructions.toArray()) if(instruction instanceof MethodInsnNode call&&call.owner.equals("java/lang/Math")&&call.name.equals("max")&&call.desc.equals("(DD)D")) {
       InsnList extra=new InsnList();
       extra.add(new LdcInsnNode(40.0));extra.add(new InsnNode(Opcodes.DMUL));
       extra.add(new MethodInsnNode(Opcodes.INVOKESTATIC,"java/lang/Math","rint","(D)D",false));
       extra.add(new LdcInsnNode(40.0));extra.add(new InsnNode(Opcodes.DDIV));
       extra.add(new MethodInsnNode(Opcodes.INVOKESTATIC,"dev/zelo/renderscale/RenderScale","getConfig","()Ldev/zelo/renderscale/config/RenderScaleConfig;",false));
       extra.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,"dev/zelo/renderscale/config/RenderScaleConfig","getMinimumScale","()D",false));
       extra.add(new MethodInsnNode(Opcodes.INVOKESTATIC,"java/lang/Math","max","(DD)D",false));
       extra.add(new MethodInsnNode(Opcodes.INVOKESTATIC,"dev/zelo/renderscale/RenderScale","getConfig","()Ldev/zelo/renderscale/config/RenderScaleConfig;",false));
       extra.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,"dev/zelo/renderscale/config/RenderScaleConfig","getScale","()F",false));extra.add(new InsnNode(Opcodes.F2D));
       extra.add(new MethodInsnNode(Opcodes.INVOKESTATIC,"java/lang/Math","min","(DD)D",false));
       method.instructions.insert(instruction,extra);edits++;
      }
     }
     if(edits!=1)throw new IllegalStateException("Expected one dynamic branch edit: "+edits);
     ClassWriter writer=new ClassWriter(ClassWriter.COMPUTE_MAXS);node.accept(writer);data=writer.toByteArray();
    }
    output.putNextEntry(new ZipEntry(e.getName()));output.write(data);output.closeEntry();
   }
  }
  if(edits!=1)throw new IllegalStateException("Class missing");System.out.println("One dynamic branch quantized; raw controller state unchanged");
 }
}
