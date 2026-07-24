window.botpress.init({
  botId: "30f332bf-dda1-4dac-a6d2-27720279e50c",
  clientId: "a4cbbe5a-a2ac-4b85-be53-cf913cb17d6e",
  configuration: {
    version: "v2",
    composerPlaceholder: "輸入問題",
    botName: "銘印鑽石",
    website: {},
    email: {
      title: "sales1@imprint-diamond.com",
      link: "sales1@imprint-diamond.com"
    },
    phone: {
      title: "+886 2-29770268",
      link: "+886 2-29770268"
    },
    termsOfService: {},
    privacyPolicy: {},
    /* Darker mint so chat pops on white pages */
    color: "#2eb8b8",
    variant: "solid",
    headerVariant: "solid",
    themeMode: "light",
    fontFamily: "Noto Sans TC",
    radius: 16,
    feedbackEnabled: false,
    footer: "",
    soundEnabled: false,
    proactiveMessageEnabled: false,
    conversationHistory: false,
    homePageEnabled: false,
    mainCardEnabled: false,
    conversationStartersEnabled: false,
    conversationStarters: [],
    conversationStartersDisplayStyle: "cards",
    /* Absolute URL so Botpress can load it from any host */
    stylesheet: (typeof location !== "undefined" ? location.origin : "") + "/static/css/botpress-text-chat.css?v=2"
  }
});
