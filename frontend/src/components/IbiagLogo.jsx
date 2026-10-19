export const IbiagLogo = ({ className = "", tone = "brand", ...props }) => (
  <img className={className} alt="IBIAG Ingredients" width="552" height="128"
    src={tone === "light" ? "/brand/ibiag-logo-light.svg" : "/brand/ibiag-logo.svg"}
    {...props} />
);
