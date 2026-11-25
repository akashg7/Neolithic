import React from 'react';
import { sceneSrc } from './kit';
export function Banner({ scene, title, sub, children }: { scene: string; title: string; sub?: string; children?: React.ReactNode }) {
  return (
    <div className="km-wrap km-herowrap"><section className="km-banner">
      <img src={sceneSrc(scene)} alt="" />
      <div className="km-wrap"><h1>{title}</h1>{sub ? <p>{sub}</p> : null}{children ? <div className="km-row">{children}</div> : null}</div>
    </section></div>
  );
}
