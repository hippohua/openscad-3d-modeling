# OpenSCAD 语法速查（对应 2021.01）

单位：毫米。角度：度。

## 3D 基本体
```
cube([w,d,h], center=false)            长方体；cube(5) 立方
sphere(r=10 | d=20, $fn=96)            球
cylinder(h=20, r=5, center=false)      圆柱
cylinder(h=20, r1=6, r2=3)             圆台（r1 底 r2 顶）
cylinder(h=20, d=10, d1=12, d2=8)      直径写法
polyhedron(points=[[x,y,z],...], faces=[[0,1,2,3],...])   自定义多面体
```

## 2D 图形（配合 extrude 使用）
```
square([w,d], center=false)   circle(r=|d=)   polygon([[x,y],...])
text("abc", size=10, font="Liberation Sans", halign="center", valign="center")
offset(r=2)          2D 轮廓外扩(+) / 内缩(-)，做壳体神器
offset(delta=-2, chamfer=true)
```

## 拉伸
```
linear_extrude(height=10, center=false, twist=0, scale=1, slices=)  2D→3D
rotate_extrude(angle=360)           2D 截面（x>=0）绕 Z 轴旋转成环
```

## 变换
```
translate([x,y,z])  rotate([rx,ry,rz])  rotate(a=45, v=[1,1,0])
scale([sx,sy,sz])   resize([w,d,h], auto=true)   mirror([nx,ny,nz])
multmatrix(m)       color("red") / color([r,g,b,a])
hull()              包络（两圆柱 hull = 圆角连接的常用技巧）
minkowski(){...}    扫掠（圆角：cube 与 sphere 做 minkowski，慢）
```

## 布尔
```
union(){...}  difference(){ 基体; 切削1; 切削2; }  intersection(){...}
```
切削体要超出基体表面，避免共面闪烁/非流形：
```
difference(){ cube(10,center=true); cylinder(h=12, r=3, center=true, $fn=64); }
```

## 控制流与复用
```
for(i=[0:5])          for(i=[0:0.5:10])       for(a=[x,y,z])
if (cond) ... else ...
let(a=1) / each（列表展开）
module part(w=10,h=5){ cube([w,w,h]); }   part(w=20);   带默认值的参数
function dist(p) = sqrt(p.x*p.x+p.y*p.y);
children()            模块内引用调用者的子节点
```

## 变量与特殊变量
- 同一作用域变量不可变，最后赋值生效；跨语句依赖用列表推导
  `[for(i=[0:3]) i*i]` 和 `concat()`。
- `$fn` 圆滑度（打印曲面 64~128，预览 32）；`$fa/$fs` 精细控制；`$t` 动画。

## 调试
```
# 高亮 / ! 只显示这个 / % 透明 / * 注释掉
echo("w=", w);        assert(w > 0, "w must be positive");
```

## 导入
```
import("part.stl")          导入网格
surface("map.png")          灰度高程图
```
