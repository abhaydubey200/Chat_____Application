"use client";

import React from "react";
import { statusDot } from "./helpers";

export default function StatusDot({ status }: { status: string }) {
  return <span className={`inline-block size-2 rounded-full ${statusDot(status)}`} />;
}
