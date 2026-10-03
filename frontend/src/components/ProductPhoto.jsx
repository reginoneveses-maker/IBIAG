import { useState } from "react";
import { ImageOff } from "lucide-react";
import { catalogImageUrl, productPhoto } from "@/lib/productPhotos";

export default function ProductPhoto({product, lang}) {
  const [failed, setFailed] = useState([]);
  const photo = productPhoto(product);
  const registered = catalogImageUrl(product.image_url);
  const custom = registered && !failed.includes(registered);
  const src = custom ? registered : photo && !failed.includes(photo.src) ? photo.src : "";
  const pt = lang !== "en";
  const ingredient = photo?.names[pt ? 0 : 1];
  return <figure>
    <div className="aspect-[4/3] overflow-hidden bg-[#EFECE6]">
      {src ? <img src={src} alt={custom ? product.name : `${pt ? "Foto real do ingrediente" : "Real ingredient photo"}: ${ingredient}`}
        loading="lazy" decoding="async" width="640" height="480"
        onError={() => setFailed(previous => [...previous, src])}
        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
        : <div className="w-full h-full flex flex-col items-center justify-center gap-2 text-[#0F382C]/60 p-5 text-center">
          <ImageOff aria-hidden="true" className="w-8 h-8" />
          <span className="text-sm">{pt ? "Foto do produto ainda não disponível" : "Product photo not available yet"}</span>
        </div>}
    </div>
    {src && !custom && <figcaption className="px-3 py-2 text-[11px] text-[#0F382C]/70 bg-[#F9F6F0]">
      <span className="block">{pt ? "Foto do ingrediente · representativa" : "Representative ingredient photo"}</span>
      <a href={photo.source} target="_blank" rel="noreferrer" className="underline" title={photo.changes} aria-label={`${pt ? "Fonte da foto de" : "Photo source for"} ${ingredient}`}>{photo.author}</a>
      {" · "}<a href={photo.licenseUrl} target="_blank" rel="noreferrer" className="underline">{photo.license}</a>
    </figcaption>}
  </figure>;
}
