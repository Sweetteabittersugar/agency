/* Agency — Provider 数据库 (Round 3: 从 utils.js 剥离) */
(function() {
  'use strict';

  let PROVIDER_DB = {
    deepseek: {name:'DeepSeek',desc:'性价比极高，中文能力强',region:'cn',price_tier:'free',api_base:'https://api.deepseek.com',default_model:'deepseek-v4-flash',register_url:'https://platform.deepseek.com/api_keys',free_credit:'500万 Token 免费额度',est_monthly:{free:'$0',mid:'$2-10',high:'$10-50'}},
    qwen: {name:'通义千问',desc:'阿里云出品，生态完善',region:'cn',price_tier:'free',api_base:'https://dashscope.aliyuncs.com/compatible-mode/v1',default_model:'qwen3-max',register_url:'https://dashscope.console.aliyun.com/',free_credit:'新用户百万 Token 免费',est_monthly:{free:'$0',mid:'$3-15',high:'$15-80'}},
    anthropic: {name:'Anthropic Claude',desc:'最强推理，安全可靠',region:'global',price_tier:'mid',api_base:'https://api.anthropic.com',default_model:'claude-sonnet-4-6',register_url:'https://console.anthropic.com/',free_credit:'无免费额度',est_monthly:{free:'—',mid:'$10-30',high:'$50-200'}},
    openai: {name:'OpenAI (GPT)',desc:'生态最成熟，模型最全',region:'global',price_tier:'mid',api_base:'https://api.openai.com/v1',default_model:'gpt-5-mini',register_url:'https://platform.openai.com/',free_credit:'无免费额度',est_monthly:{free:'—',mid:'$10-30',high:'$50-200'}},
    google: {name:'Google Gemini',desc:'多模态能力强，免费额度慷慨',region:'global',price_tier:'free',api_base:'https://generativelanguage.googleapis.com/v1beta/openai',default_model:'gemini-2.5-flash',register_url:'https://aistudio.google.com/apikey',free_credit:'免费层额度充足',est_monthly:{free:'$0',mid:'$5-20',high:'$20-80'}},
    xai: {name:'xAI (Grok)',desc:'Musk 出品，实时信息',region:'global',price_tier:'mid',api_base:'https://api.x.ai/v1',default_model:'grok-4.3',register_url:'https://x.ai/api',free_credit:'每月有免费额度',est_monthly:{free:'$0',mid:'$5-25',high:'$25-100'}},
    zhipu: {name:'智谱 GLM',desc:'国产开源先锋，GLM-5 免费额度',region:'cn',price_tier:'free',api_base:'https://open.bigmodel.cn/api/paas/v4',default_model:'GLM-5.1',register_url:'https://open.bigmodel.cn/',free_credit:'GLM-4-Flash 免费',est_monthly:{free:'$0',mid:'$5-25',high:'$25-100'}},
    custom: {name:'自定义端点',desc:'兼容 OpenAI 格式的任意服务',region:'any',price_tier:'any',api_base:'https://your-api-endpoint.com/v1',default_model:'gpt-3.5-turbo',register_url:'',free_credit:'取决于你的服务商',est_monthly:{free:'—',mid:'—',high:'—'}}
  };

  window.PROVIDER_DB = PROVIDER_DB;
})();
