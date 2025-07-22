export const workflowConfigs = {
  'sd_basic': {
    name: 'SD Basic',
    description: '基础SD1.5工作流',
    defaultResolution: '512x512',
    recommendedResolutions: ['512x512', '768x768'],
    models: [
      {
        value: 'SD\\majicmixRealistic_v7.safetensors',
        text: 'MajicMix - 写实 + 二次元混合模型,介于真实与动漫之间',
        recommended: false
      },
      {
        value: 'SD\\realisticVisionV60B1_v51HyperVAE.safetensors',
        text: '⭐Realistic Vision - 超写实人像模型,擅长女性肖像、写真照',
        recommended: true
      },
      {
        value: 'SD\\onlyrealistic_v30BakedVAE.safetensors',
        text: 'Onlyrealistic - 写实风,人像的真实质感',
        recommended: false
      }
    ]
  },
  'sdxl_basic': {
    name: 'SDXL Basic',
    description: '高分辨率SDXL工作流',
    defaultResolution: '1024x1024',
    recommendedResolutions: ['1024x1024', '832x1216', '1216x832', '1344x768'],
    models: [
      {
        value: 'SDXL\\sd_xl_base_1.0.safetensors',
        text: 'SDXL Base - 官方 SDXL 基础模型',
        recommended: false
      },
      {
        value: 'SDXL\\juggernautXL_juggXIByRundiffusion_2.safetensors',
        text: '⭐JuggernautXL - 多风格混合（写实 + 美型 + 半写实 + 插画）',
        recommended: true
      },
      {
        value: 'SDXL\\Wanxiang_XLSuper_RealisticV8.4_V8.4.safetensors',
        text: 'Wanxiang_Super_Realistic - 基于 SDXL 官方模型微调优化,超写实风格人像与场景生成',
        recommended: false
      },
      {
        value: 'SDXL\\turbovisionxlSuperFastXLBasedOnNew_tvxlV431Bakedvae.safetensors',
        text: 'SDXL Base - 高速度 + 高写实质量 的混合模型',
        recommended: false
      }
    ]
  }
};

export const defaultParams = {
  sd_basic: {
    width: 512,
    height: 512,
    seed: -1,
    checkpoint: 'SD\\realisticVisionV60B1_v51HyperVAE.safetensors'
  },
  sdxl_basic: {
    width: 1024,
    height: 1024,
    seed: -1,
    checkpoint: 'SDXL\\juggernautXL_juggXIByRundiffusion_2.safetensors'
  }
}; 