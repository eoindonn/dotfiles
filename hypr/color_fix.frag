#version 300 es
precision mediump float;

// In GLSL 300, 'varying' becomes 'in'
in vec2 v_texcoord;

// The output target pixel color structure
out vec4 fragColor;

// The texture data sampled from the desktop compositor
uniform sampler2D tex;

void main() {
    // texture2D is deprecated; we use native texture() sampling in 300 es
    vec4 color = texture(tex, v_texcoord);
    
    // Applying the 6300K DCI-P3 monitor correction matrix
    float r = color.r * 1.0;
    float g = color.g * 0.94; 
    float b = color.b * 1.02;
    
    // Output the modified color cleanly
    fragColor = vec4(r, g, b, color.a);
}